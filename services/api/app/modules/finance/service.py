"""Regras financeiras: contas, lançamentos, caixa, DRE e comissões."""

import csv
import io
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.api.schemas.finance import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    AccountBalanceResponse,
    CashFlowResponse,
    CommissionItemResponse,
    CommissionSummaryResponse,
    DreResponse,
    FinancialAccountResponse,
    FinancialEntryCreateRequest,
    FinancialEntryResponse,
    SaleItemResponse,
    SalesResponse,
    TitheDeliveryCreateRequest,
)
from app.core.config import settings as app_settings
from app.models import (
    AccountType,
    Appointment,
    AppointmentStatus,
    CommissionBase,
    FinancialAccount,
    FinancialCategory,
    FinancialEntry,
    FinancialEntryStatus,
    FinancialEntryType,
    TenantSettings,
    TitheDelivery,
)
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

INCOME_CATEGORY_VALUES = tuple(category.value for category in INCOME_CATEGORIES)
DEDUCTION_CATEGORIES = (
    FinancialCategory.TAX.value,
    FinancialCategory.CARD_FEE.value,
)
COST_CATEGORIES = (
    FinancialCategory.SUPPLIES.value,
    FinancialCategory.COMMISSION.value,
)
OPERATING_CATEGORIES = (
    FinancialCategory.RENT.value,
    FinancialCategory.UTILITY.value,
    FinancialCategory.MARKETING.value,
    FinancialCategory.PAYROLL.value,
    FinancialCategory.OTHER_EXPENSE.value,
)


class FinanceValidationError(Exception):
    """Dados inválidos para o lançamento/conta."""


class FinanceNotFoundError(Exception):
    """Conta ou lançamento inexistente."""


class FinanceConflictError(Exception):
    """Nome de conta já utilizado."""


class FinanceInUseError(Exception):
    """Conta possui lançamentos e não pode ser excluída."""


@dataclass
class _CommissionAccumulator:
    name: str
    count: int = 0
    gross: Decimal = field(default_factory=lambda: ZERO)
    commission: Decimal = field(default_factory=lambda: ZERO)


def _entry_response(entry: FinancialEntry) -> FinancialEntryResponse:
    return FinancialEntryResponse(
        id=entry.id,
        account_id=entry.account_id,
        type=entry.type,
        category=entry.category,
        description=entry.description,
        amount=entry.amount,
        competence_date=entry.competence_date,
        cash_date=entry.cash_date,
        status=entry.status,
        appointment_id=entry.appointment_id,
    )


def _account_response(account: FinancialAccount) -> FinancialAccountResponse:
    return FinancialAccountResponse(
        id=account.id,
        name=account.name,
        type=account.type,
        initial_balance=account.initial_balance,
        is_active=account.is_active,
    )


def _period_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(app_settings.default_tenant_timezone)
    start = datetime.combine(from_date, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(
        to_date + timedelta(days=1),
        time.min,
        tzinfo=tz,
    ).astimezone(UTC)
    return start, end


def _csv_safe(value: str) -> str:
    """Evita injeção de fórmula ao abrir o CSV no Excel/Sheets."""
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


async def create_account(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    account_type: AccountType,
    initial_balance: Decimal,
) -> FinancialAccountResponse:
    account = FinancialAccount(
        tenant_id=tenant_id,
        name=name.strip(),
        type=account_type,
        initial_balance=initial_balance,
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_financial_accounts_tenant_id_name" in str(exc.orig):
            raise FinanceConflictError from exc
        raise
    return _account_response(account)


async def list_accounts(session: AsyncSession) -> list[FinancialAccountResponse]:
    accounts = (
        await session.scalars(
            select(FinancialAccount).order_by(FinancialAccount.name)
        )
    ).all()
    return [_account_response(account) for account in accounts]


async def get_account(
    session: AsyncSession,
    account_id: UUID,
) -> FinancialAccount:
    account = await session.get(FinancialAccount, account_id)
    if account is None:
        raise FinanceNotFoundError
    return account


async def update_account(
    session: AsyncSession,
    *,
    account: FinancialAccount,
    changes: dict[str, object],
) -> FinancialAccountResponse:
    if "name" in changes:
        account.name = str(changes["name"]).strip()
    if "is_active" in changes:
        account.is_active = bool(changes["is_active"])
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_financial_accounts_tenant_id_name" in str(exc.orig):
            raise FinanceConflictError from exc
        raise
    return _account_response(account)


async def delete_account(
    session: AsyncSession,
    *,
    account: FinancialAccount,
) -> None:
    await session.delete(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise FinanceInUseError from exc


async def create_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    created_by: UUID,
    body: FinancialEntryCreateRequest,
) -> FinancialEntryResponse:
    await get_account(session, body.account_id)
    entry = FinancialEntry(
        tenant_id=tenant_id,
        account_id=body.account_id,
        type=body.type,
        category=body.category,
        description=body.description.strip(),
        amount=body.amount,
        competence_date=body.competence_date,
        cash_date=body.cash_date,
        status=body.status,
        appointment_id=body.appointment_id,
        created_by=created_by,
    )
    session.add(entry)
    await session.commit()
    return _entry_response(entry)


async def list_entries(
    session: AsyncSession,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    entry_status: FinancialEntryStatus | None = None,
    account_id: UUID | None = None,
) -> list[FinancialEntryResponse]:
    query = select(FinancialEntry).order_by(
        FinancialEntry.competence_date.desc(),
        FinancialEntry.created_at.desc(),
    )
    if from_date is not None:
        query = query.where(FinancialEntry.competence_date >= from_date)
    if to_date is not None:
        query = query.where(FinancialEntry.competence_date <= to_date)
    if entry_status is not None:
        query = query.where(FinancialEntry.status == entry_status)
    if account_id is not None:
        query = query.where(FinancialEntry.account_id == account_id)
    entries = (await session.scalars(query.limit(500))).all()
    return [_entry_response(entry) for entry in entries]


async def get_entry(
    session: AsyncSession,
    entry_id: UUID,
) -> FinancialEntry:
    entry = await session.get(FinancialEntry, entry_id)
    if entry is None:
        raise FinanceNotFoundError
    return entry


async def update_entry(
    session: AsyncSession,
    *,
    entry: FinancialEntry,
    changes: dict[str, object],
) -> FinancialEntryResponse:
    if "account_id" in changes:
        account_id = changes["account_id"]
        if not isinstance(account_id, UUID):
            raise FinanceValidationError("account_id inválido")
        await get_account(session, account_id)
    if "category" in changes:
        category = changes["category"]
        allowed = (
            INCOME_CATEGORIES
            if entry.type == FinancialEntryType.INCOME
            else EXPENSE_CATEGORIES
        )
        if category not in allowed:
            raise FinanceValidationError("categoria incompatível com o tipo")

    for attribute in (
        "account_id",
        "category",
        "description",
        "amount",
        "competence_date",
        "cash_date",
        "status",
    ):
        if attribute in changes:
            setattr(entry, attribute, changes[attribute])
    if (
        entry.status == FinancialEntryStatus.PAID
        and entry.cash_date is None
    ):
        raise FinanceValidationError("cash_date é obrigatório para lançamento pago")
    await session.commit()
    return _entry_response(entry)


async def delete_entry(
    session: AsyncSession,
    *,
    entry: FinancialEntry,
) -> None:
    await session.delete(entry)
    await session.commit()


async def cash_flow(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> CashFlowResponse:
    initial = await session.scalar(
        select(func.coalesce(func.sum(FinancialAccount.initial_balance), 0))
    )
    before = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            FinancialEntry.type == FinancialEntryType.INCOME,
                            FinancialEntry.amount,
                        ),
                        else_=-FinancialEntry.amount,
                    )
                ),
                0,
            )
        ).where(
            FinancialEntry.status == FinancialEntryStatus.PAID,
            FinancialEntry.cash_date < from_date,
        )
    )
    flows = (
        await session.execute(
            select(
                FinancialEntry.type,
                func.coalesce(func.sum(FinancialEntry.amount), 0),
            )
            .where(
                FinancialEntry.status == FinancialEntryStatus.PAID,
                FinancialEntry.cash_date >= from_date,
                FinancialEntry.cash_date <= to_date,
            )
            .group_by(FinancialEntry.type)
        )
    ).all()
    totals = {entry_type: amount for entry_type, amount in flows}
    inflows = Decimal(totals.get(FinancialEntryType.INCOME, ZERO))
    outflows = Decimal(totals.get(FinancialEntryType.EXPENSE, ZERO))
    opening = Decimal(initial or 0) + Decimal(before or 0)
    return CashFlowResponse(
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening.quantize(CENT),
        inflows=inflows.quantize(CENT),
        outflows=outflows.quantize(CENT),
        closing_balance=(opening + inflows - outflows).quantize(CENT),
    )


async def account_balances(
    session: AsyncSession,
) -> list[AccountBalanceResponse]:
    accounts = (
        await session.scalars(
            select(FinancialAccount).order_by(FinancialAccount.name)
        )
    ).all()
    rows = (
        await session.execute(
            select(
                FinancialEntry.account_id,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                FinancialEntry.type
                                == FinancialEntryType.INCOME,
                                FinancialEntry.amount,
                            ),
                            else_=-FinancialEntry.amount,
                        )
                    ),
                    0,
                ),
            )
            .where(
                FinancialEntry.status == FinancialEntryStatus.PAID,
                FinancialEntry.cash_date.is_not(None),
            )
            .group_by(FinancialEntry.account_id)
        )
    ).all()
    movement = {account_id: Decimal(str(value)) for account_id, value in rows}
    return [
        AccountBalanceResponse(
            account_id=account.id,
            name=account.name,
            type=account.type,
            initial_balance=account.initial_balance,
            balance=(
                account.initial_balance
                + movement.get(account.id, ZERO)
            ).quantize(CENT),
        )
        for account in accounts
    ]


async def _sum_by_categories(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    categories: tuple[str, ...],
) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(
            FinancialEntry.status == FinancialEntryStatus.PAID,
            FinancialEntry.competence_date >= from_date,
            FinancialEntry.competence_date <= to_date,
            FinancialEntry.category.in_(categories),
        )
    )
    return Decimal(value or 0)


async def commission_items(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    collaborator_id: UUID | None = None,
) -> list[CommissionItemResponse]:
    start, end = _period_bounds(from_date, to_date)
    query = select(Appointment).where(
        Appointment.status == AppointmentStatus.COMPLETED,
        Appointment.starts_at >= start,
        Appointment.starts_at < end,
    )
    if collaborator_id is not None:
        query = query.where(Appointment.collaborator_id == collaborator_id)
    appointments = (
        await session.scalars(query.order_by(Appointment.starts_at))
    ).all()

    grouped: dict[UUID, _CommissionAccumulator] = {}
    for appointment in appointments:
        collaborator = appointment.collaborator
        service = appointment.service
        base = service.price
        if collaborator.commission_base == CommissionBase.NET:
            base = service.price - service.cost
        amount = ZERO
        if collaborator.commission_percentage:
            amount += base * collaborator.commission_percentage / Decimal("100")
        if collaborator.commission_fixed:
            amount += collaborator.commission_fixed
        accumulator = grouped.get(collaborator.id)
        if accumulator is None:
            accumulator = _CommissionAccumulator(name=collaborator.full_name)
            grouped[collaborator.id] = accumulator
        accumulator.count += 1
        accumulator.gross += service.price
        accumulator.commission += amount

    return [
        CommissionItemResponse(
            collaborator_id=collaborator_id,
            collaborator_name=accumulator.name,
            completed_appointments=accumulator.count,
            gross_revenue=accumulator.gross.quantize(CENT),
            commission_amount=accumulator.commission.quantize(CENT),
        )
        for collaborator_id, accumulator in grouped.items()
    ]


async def commission_summary(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    collaborator_id: UUID | None = None,
) -> CommissionSummaryResponse:
    items = await commission_items(
        session,
        from_date=from_date,
        to_date=to_date,
        collaborator_id=collaborator_id,
    )
    total = sum((item.commission_amount for item in items), ZERO)
    return CommissionSummaryResponse(
        from_date=from_date,
        to_date=to_date,
        items=items,
        total=total.quantize(CENT),
    )


async def dre(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    from_date: date,
    to_date: date,
) -> DreResponse:
    gross_revenue = await _sum_by_categories(
        session,
        from_date=from_date,
        to_date=to_date,
        categories=INCOME_CATEGORY_VALUES,
    )
    deductions = await _sum_by_categories(
        session,
        from_date=from_date,
        to_date=to_date,
        categories=DEDUCTION_CATEGORIES,
    )
    costs = await _sum_by_categories(
        session,
        from_date=from_date,
        to_date=to_date,
        categories=COST_CATEGORIES,
    )
    operating = await _sum_by_categories(
        session,
        from_date=from_date,
        to_date=to_date,
        categories=OPERATING_CATEGORIES,
    )
    net_profit = gross_revenue - deductions - costs - operating
    commissions = await commission_items(
        session,
        from_date=from_date,
        to_date=to_date,
    )
    commissions_accrued = sum(
        (item.commission_amount for item in commissions),
        ZERO,
    )

    tenant_settings = await session.get(TenantSettings, tenant_id)
    # A configuração é lida via tenant atual (RLS); busca explícita pelo id
    # do tenant não é necessária, pois a sessão já está isolada.
    tithe_enabled = (
        tenant_settings.enable_tithe_and_offering
        if tenant_settings is not None
        else False
    )
    tithe_percentage = (
        tenant_settings.tithe_percentage
        if tenant_settings is not None
        else Decimal("10.00")
    )
    offering = (
        tenant_settings.offering_amount
        if tenant_settings is not None
        else ZERO
    )
    tithe = (
        max(net_profit, ZERO) * tithe_percentage / Decimal("100")
        if tithe_enabled
        else ZERO
    )
    after = net_profit - tithe - (offering if tithe_enabled else ZERO)
    return DreResponse(
        from_date=from_date,
        to_date=to_date,
        gross_revenue=gross_revenue.quantize(CENT),
        deductions=deductions.quantize(CENT),
        costs=costs.quantize(CENT),
        operating_expenses=operating.quantize(CENT),
        net_profit=net_profit.quantize(CENT),
        commissions_accrued=commissions_accrued.quantize(CENT),
        tithe_enabled=tithe_enabled,
        tithe_percentage=tithe_percentage,
        tithe_amount=tithe.quantize(CENT),
        offering_amount=(offering if tithe_enabled else ZERO).quantize(CENT),
        after_tithe_and_offering=after.quantize(CENT),
    )


async def sales(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> SalesResponse:
    start, end = _period_bounds(from_date, to_date)
    appointments = (
        await session.scalars(
            select(Appointment)
            .where(
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.starts_at >= start,
                Appointment.starts_at < end,
            )
            .order_by(Appointment.starts_at)
        )
    ).all()
    items: list[SaleItemResponse] = []
    for appointment in appointments:
        collaborator = appointment.collaborator
        service = appointment.service
        base = service.price
        if collaborator.commission_base == CommissionBase.NET:
            base = service.price - service.cost
        commission = ZERO
        if collaborator.commission_percentage:
            commission += base * collaborator.commission_percentage / Decimal("100")
        if collaborator.commission_fixed:
            commission += collaborator.commission_fixed
        net = service.price - service.cost - commission
        items.append(
            SaleItemResponse(
                appointment_id=appointment.id,
                starts_at=appointment.starts_at,
                client_name=appointment.client.full_name,
                service_name=service.name,
                collaborator_name=collaborator.full_name,
                gross_amount=service.price.quantize(CENT),
                cost_amount=service.cost.quantize(CENT),
                commission_amount=commission.quantize(CENT),
                net_amount=net.quantize(CENT),
            )
        )
    gross_total = sum((item.gross_amount for item in items), ZERO)
    net_total = sum((item.net_amount for item in items), ZERO)
    return SalesResponse(
        from_date=from_date,
        to_date=to_date,
        items=items,
        gross_total=gross_total.quantize(CENT),
        net_total=net_total.quantize(CENT),
    )


async def export_csv(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> str:
    entries = (
        await session.scalars(
            select(FinancialEntry)
            .where(
                FinancialEntry.competence_date >= from_date,
                FinancialEntry.competence_date <= to_date,
            )
            .order_by(FinancialEntry.competence_date, FinancialEntry.created_at)
        )
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "competencia",
            "caixa",
            "tipo",
            "categoria",
            "descricao",
            "valor",
            "status",
            "conta",
        ]
    )
    for entry in entries:
        writer.writerow(
            [
                entry.competence_date.isoformat(),
                entry.cash_date.isoformat() if entry.cash_date else "",
                entry.type.value,
                entry.category.value,
                _csv_safe(entry.description),
                f"{entry.amount:.2f}",
                entry.status.value,
                _csv_safe(entry.account.name),
            ]
        )
    return buffer.getvalue()


async def list_tithe_deliveries(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> list[TitheDelivery]:
    return list(
        (
            await session.scalars(
                select(TitheDelivery)
                .where(
                    TitheDelivery.competence_date >= from_date,
                    TitheDelivery.competence_date <= to_date,
                )
                .order_by(TitheDelivery.competence_date.desc())
            )
        ).all()
    )


async def create_tithe_delivery(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_id: UUID,
    body: TitheDeliveryCreateRequest,
) -> TitheDelivery:
    tenant_settings = await session.get(TenantSettings, tenant_id)
    if tenant_settings is None or not tenant_settings.enable_tithe_and_offering:
        raise FinanceValidationError(
            "Dízimo e oferta estão desativados nas configurações"
        )
    delivery = TitheDelivery(
        id=uuid4(),
        tenant_id=tenant_id,
        competence_date=body.competence_date,
        tithe_amount=body.tithe_amount,
        offering_amount=body.offering_amount,
        note=body.note.strip() if body.note else None,
        created_by=actor_id,
    )
    session.add(delivery)
    await session.commit()
    return delivery


async def delete_tithe_delivery(
    session: AsyncSession,
    delivery: TitheDelivery,
) -> None:
    await session.delete(delivery)
    await session.commit()
