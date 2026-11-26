"""Regras de folha, adiantamentos e pró-labore."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.payroll import (
    PayrollEntryCreateRequest,
    PayrollEntryUpdateRequest,
)
from app.models import (
    FinancialAccount,
    FinancialCategory,
    FinancialEntry,
    FinancialEntryStatus,
    FinancialEntryType,
    PayrollEntry,
    User,
)


class PayrollNotFoundError(Exception):
    """Verba de folha inexistente."""


class PayrollValidationError(Exception):
    """Dados de folha inválidos."""


async def list_payroll(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    user_id: UUID | None = None,
) -> list[tuple[PayrollEntry, str]]:
    query = (
        select(PayrollEntry, User.full_name)
        .join(User, User.id == PayrollEntry.user_id)
        .where(
            PayrollEntry.competence_date >= from_date,
            PayrollEntry.competence_date <= to_date,
        )
        .order_by(
            PayrollEntry.competence_date.desc(),
            PayrollEntry.created_at.desc(),
        )
    )
    if user_id is not None:
        query = query.where(PayrollEntry.user_id == user_id)
    rows = (await session.execute(query)).all()
    return [(entry, name) for entry, name in rows]


async def get_payroll_entry(
    session: AsyncSession,
    entry_id: UUID,
) -> PayrollEntry:
    entry = await session.get(PayrollEntry, entry_id)
    if entry is None:
        raise PayrollNotFoundError
    return entry


async def _get_account(
    session: AsyncSession,
    account_id: UUID,
) -> FinancialAccount:
    account = await session.get(FinancialAccount, account_id)
    if account is None:
        raise PayrollValidationError("Conta financeira não encontrada")
    return account


async def _get_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise PayrollValidationError("Usuário não encontrado")
    return user


async def _sync_financial_entry(
    session: AsyncSession,
    *,
    entry: PayrollEntry,
    actor_id: UUID,
    account_id: UUID | None,
) -> None:
    linked: FinancialEntry | None = None
    if entry.financial_entry_id is not None:
        linked = await session.get(FinancialEntry, entry.financial_entry_id)

    if entry.status == FinancialEntryStatus.PENDING:
        if linked is not None:
            await session.delete(linked)
            entry.financial_entry_id = None
        return

    if entry.cash_date is None:
        raise PayrollValidationError("cash_date é obrigatório para folha paga")
    target_account_id = account_id or (linked.account_id if linked else None)
    if target_account_id is None:
        raise PayrollValidationError("account_id é obrigatório para folha paga")
    await _get_account(session, target_account_id)

    if linked is None:
        linked = FinancialEntry(
            id=uuid4(),
            tenant_id=entry.tenant_id,
            account_id=target_account_id,
            type=FinancialEntryType.EXPENSE,
            category=FinancialCategory.PAYROLL,
            description=f"Folha: {entry.description}",
            amount=entry.amount,
            competence_date=entry.competence_date,
            cash_date=entry.cash_date,
            status=FinancialEntryStatus.PAID,
            created_by=actor_id,
        )
        session.add(linked)
        await session.flush()
        entry.financial_entry_id = linked.id
        return

    linked.account_id = target_account_id
    linked.description = f"Folha: {entry.description}"
    linked.amount = entry.amount
    linked.competence_date = entry.competence_date
    linked.cash_date = entry.cash_date
    linked.status = FinancialEntryStatus.PAID


async def create_payroll_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_id: UUID,
    body: PayrollEntryCreateRequest,
) -> PayrollEntry:
    await _get_user(session, body.user_id)
    entry = PayrollEntry(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=body.user_id,
        kind=body.kind.value,
        description=body.description.strip(),
        amount=body.amount,
        competence_date=body.competence_date,
        status=body.status,
        cash_date=body.cash_date,
    )
    session.add(entry)
    await _sync_financial_entry(
        session,
        entry=entry,
        actor_id=actor_id,
        account_id=body.account_id,
    )
    await session.commit()
    return entry


async def update_payroll_entry(
    session: AsyncSession,
    *,
    entry: PayrollEntry,
    actor_id: UUID,
    body: PayrollEntryUpdateRequest,
) -> PayrollEntry:
    changes = body.model_dump(exclude_unset=True)
    for field in ("kind", "description", "amount", "competence_date", "status"):
        if field not in changes or changes[field] is None:
            continue
        value = changes[field]
        if field == "kind":
            value = value.value
        if field == "description":
            value = str(value).strip()
        setattr(entry, field, value)
    if "cash_date" in changes:
        entry.cash_date = changes["cash_date"]
    await _sync_financial_entry(
        session,
        entry=entry,
        actor_id=actor_id,
        account_id=changes.get("account_id"),
    )
    await session.commit()
    return entry


async def delete_payroll_entry(
    session: AsyncSession,
    *,
    entry: PayrollEntry,
) -> None:
    if entry.financial_entry_id is not None:
        linked = await session.get(FinancialEntry, entry.financial_entry_id)
        if linked is not None:
            await session.delete(linked)
    await session.delete(entry)
    await session.commit()


def total_amount(entries: list[PayrollEntry]) -> Decimal:
    return sum((entry.amount for entry in entries), Decimal("0.00"))
