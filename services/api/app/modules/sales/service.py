"""Regras da comanda digital."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.clients import ClientCreditUsageCreateRequest
from app.api.schemas.sales import (
    SaleCloseRequest,
    SaleCreditRequest,
    SaleItemCreateRequest,
    SaleUpdateRequest,
)
from app.db.rls import set_tenant_context
from app.models import (
    Appointment,
    AppointmentStatus,
    Client,
    ClientCredit,
    ClientCreditUsage,
    FinancialCategory,
    FinancialEntry,
    FinancialEntryStatus,
    FinancialEntryType,
    InventoryItem,
    Sale,
    SaleItem,
    SaleItemCategory,
    SaleStatus,
    Service,
    StockMovement,
)
from app.modules.credits.service import (
    ClientCreditValidationError,
    remaining_amount,
    use_credit,
)

CENT = Decimal("0.01")


class SaleNotFoundError(Exception):
    """Comanda inexistente."""


class SaleValidationError(Exception):
    """Comanda em estado inválido."""


class SaleScopeError(Exception):
    """Comanda fora do escopo do usuário."""


async def get_sale(session: AsyncSession, sale_id: UUID) -> Sale:
    sale = await session.get(Sale, sale_id)
    if sale is None:
        raise SaleNotFoundError
    return sale


async def list_sales(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    status: SaleStatus | None = None,
) -> list[Sale]:
    query = (
        select(Sale)
        .where(
            Sale.created_at
            >= datetime.combine(from_date, datetime.min.time(), tzinfo=UTC),
            Sale.created_at
            < datetime.combine(to_date, datetime.max.time(), tzinfo=UTC),
        )
        .order_by(Sale.created_at.desc())
    )
    if status is not None:
        query = query.where(Sale.status == status)
    return list((await session.scalars(query)).all())


def _recalculate(sale: Sale) -> None:
    subtotal = sum((item.total for item in sale.items), Decimal("0.00"))
    sale.subtotal = subtotal.quantize(CENT)
    discount = min(sale.discount, sale.subtotal)
    sale.discount = discount
    sale.credit_amount = min(sale.credit_amount, sale.subtotal - discount)
    sale.total = max(
        sale.subtotal - sale.discount - sale.credit_amount,
        Decimal("0.00"),
    ).quantize(CENT)


async def create_from_appointment(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_id: UUID,
    appointment_id: UUID,
) -> Sale:
    appointment = await session.get(Appointment, appointment_id)
    if appointment is None:
        raise SaleNotFoundError
    if appointment.status in (
        AppointmentStatus.CANCELLED,
        AppointmentStatus.EXPIRED,
    ):
        raise SaleValidationError("Agendamento cancelado/expirado")

    existing = await session.scalar(
        select(Sale)
        .where(
            Sale.appointment_id == appointment_id,
            Sale.status == SaleStatus.OPEN,
        )
        .order_by(Sale.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing
    paid = await session.scalar(
        select(Sale)
        .where(
            Sale.appointment_id == appointment_id,
            Sale.status == SaleStatus.PAID,
        )
        .limit(1)
    )
    if paid is not None:
        raise SaleValidationError("Comanda já paga para este agendamento")

    service = appointment.service
    client = await session.get(Client, appointment.client_id)
    if client is None:
        raise SaleNotFoundError
    price = service.price
    sale = Sale(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=appointment.client_id,
        appointment_id=appointment.id,
        collaborator_id=appointment.collaborator_id,
        status=SaleStatus.OPEN,
        subtotal=price,
        discount=Decimal("0.00"),
        credit_amount=Decimal("0.00"),
        total=price,
        created_by=actor_id,
        client=client,
    )
    sale.items.append(
        SaleItem(
            id=uuid4(),
            tenant_id=tenant_id,
            service_id=service.id,
            category=SaleItemCategory.SERVICE,
            description=service.name,
            quantity=1,
            unit_price=price,
            cost=service.cost,
            total=price,
        )
    )
    session.add(sale)
    await session.commit()
    await set_tenant_context(session, tenant_id)
    return sale


async def add_item(
    session: AsyncSession,
    *,
    sale: Sale,
    tenant_id: UUID,
    body: SaleItemCreateRequest,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Comanda não está aberta")

    description = body.description
    unit_price = body.unit_price
    cost = body.cost or Decimal("0.00")
    if body.service_id is not None:
        service = await session.get(Service, body.service_id)
        if service is None:
            raise SaleValidationError("Serviço não encontrado")
        description = description or service.name
        unit_price = unit_price if unit_price is not None else service.price
        cost = body.cost if body.cost is not None else service.cost
    if body.inventory_item_id is not None:
        inventory = await session.get(InventoryItem, body.inventory_item_id)
        if inventory is None:
            raise SaleValidationError("Produto/insumo não encontrado")
        description = description or inventory.name
        unit_price = (
            unit_price if unit_price is not None else inventory.unit_cost
        )
        cost = body.cost if body.cost is not None else inventory.unit_cost

    if description is None or unit_price is None:
        raise SaleValidationError("Item incompleto")

    quantity = body.quantity
    item = SaleItem(
        id=uuid4(),
        tenant_id=tenant_id,
        sale_id=sale.id,
        service_id=body.service_id,
        inventory_item_id=body.inventory_item_id,
        category=body.category,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        cost=cost,
        total=(unit_price * quantity).quantize(CENT),
    )
    sale.items.append(item)
    _recalculate(sale)
    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return sale


async def remove_item(
    session: AsyncSession,
    *,
    sale: Sale,
    item_id: UUID,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Comanda não está aberta")
    item = next((entry for entry in sale.items if entry.id == item_id), None)
    if item is None:
        raise SaleValidationError("Item não encontrado")
    sale.items.remove(item)
    await session.delete(item)
    _recalculate(sale)
    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return sale


async def update_sale(
    session: AsyncSession,
    *,
    sale: Sale,
    body: SaleUpdateRequest,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Comanda não está aberta")
    changes = body.model_dump(exclude_unset=True)
    if "discount" in changes and changes["discount"] is not None:
        sale.discount = Decimal(str(changes["discount"]))
    if "notes" in changes:
        sale.notes = changes["notes"]
    _recalculate(sale)
    if sale.discount > sale.subtotal:
        raise SaleValidationError("Desconto maior que o subtotal")
    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return sale


async def apply_credit(
    session: AsyncSession,
    *,
    sale: Sale,
    actor_id: UUID,
    body: SaleCreditRequest,
    today: date,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Comanda não está aberta")
    credit = await session.get(ClientCredit, body.credit_id)
    if credit is None or credit.client_id != sale.client_id:
        raise SaleValidationError("Crédito não pertence ao cliente")
    if body.amount > remaining_amount(credit):
        raise SaleValidationError("Saldo insuficiente no crédito")
    available = sale.subtotal - sale.discount - sale.credit_amount
    if body.amount > available:
        raise SaleValidationError("Crédito maior que o saldo da comanda")

    sale.credit_amount += body.amount
    _recalculate(sale)
    try:
        await use_credit(
            session,
            credit=credit,
            actor_id=actor_id,
            body=ClientCreditUsageCreateRequest(
                amount=body.amount,
                appointment_id=sale.appointment_id,
                note=f"Comanda {sale.id}",
            ),
            today=today,
            sale_id=sale.id,
        )
    except ClientCreditValidationError as exc:
        raise SaleValidationError(str(exc)) from exc
    await set_tenant_context(session, sale.tenant_id)
    return sale


def _income_category(sale: Sale) -> FinancialCategory:
    categories = {item.category for item in sale.items}
    if categories == {SaleItemCategory.PACKAGE}:
        return FinancialCategory.PACKAGE
    if categories == {SaleItemCategory.PRODUCT}:
        return FinancialCategory.PRODUCT
    if categories == {SaleItemCategory.OTHER}:
        return FinancialCategory.OTHER_INCOME
    return FinancialCategory.SERVICE


async def close_sale(
    session: AsyncSession,
    *,
    sale: Sale,
    actor_id: UUID,
    body: SaleCloseRequest,
    today: date,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Comanda não está aberta")
    if sale.subtotal <= 0:
        raise SaleValidationError("Comanda sem itens")

    for item in sale.items:
        if item.inventory_item_id is None:
            continue
        inventory = await session.get(InventoryItem, item.inventory_item_id)
        if inventory is None:
            continue
        if Decimal(item.quantity) > inventory.quantity:
            raise SaleValidationError(
                f"Estoque insuficiente para {inventory.name}"
            )

    sale.status = SaleStatus.PAID
    sale.payment_method = body.payment_method
    sale.account_id = body.account_id
    sale.closed_at = datetime.now(UTC)
    if body.notes:
        sale.notes = body.notes

    if sale.total > 0:
        entry = FinancialEntry(
            id=uuid4(),
            tenant_id=sale.tenant_id,
            account_id=body.account_id,
            type=FinancialEntryType.INCOME,
            category=_income_category(sale),
            description=f"Comanda {sale.id.hex[:8]}",
            amount=sale.total,
            competence_date=today,
            cash_date=today,
            status=FinancialEntryStatus.PAID,
            appointment_id=sale.appointment_id,
            created_by=actor_id,
        )
        session.add(entry)
        await session.flush()
        sale.financial_entry_id = entry.id

    for item in sale.items:
        if item.inventory_item_id is None:
            continue
        inventory = await session.get(InventoryItem, item.inventory_item_id)
        if inventory is None:
            continue
        inventory.quantity -= Decimal(item.quantity)
        session.add(
            StockMovement(
                id=uuid4(),
                tenant_id=sale.tenant_id,
                item_id=inventory.id,
                kind="OUT",
                quantity=Decimal(item.quantity),
                reason=f"Comanda {sale.id.hex[:8]}",
                created_by=actor_id,
            )
        )

    if sale.appointment_id is not None:
        appointment = await session.get(Appointment, sale.appointment_id)
        if appointment is not None and appointment.status not in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.EXPIRED,
            AppointmentStatus.NO_SHOW,
        ):
            appointment.status = AppointmentStatus.COMPLETED
            appointment.deposit_expires_at = None

    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return sale


async def cancel_sale(
    session: AsyncSession,
    *,
    sale: Sale,
) -> Sale:
    if sale.status != SaleStatus.OPEN:
        raise SaleValidationError("Somente comanda aberta pode ser cancelada")
    usages = (
        await session.scalars(
            select(ClientCreditUsage).where(ClientCreditUsage.sale_id == sale.id)
        )
    ).all()
    for usage in usages:
        credit = await session.get(ClientCredit, usage.credit_id)
        if credit is not None:
            credit.used_amount = max(
                credit.used_amount - usage.amount,
                Decimal("0.00"),
            )
        await session.delete(usage)
    sale.status = SaleStatus.CANCELLED
    sale.cancelled_at = datetime.now(UTC)
    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return sale
