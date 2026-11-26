"""Regras de estoque de insumos."""

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.inventory import (
    InventoryItemCreateRequest,
    StockMovementCreateRequest,
)
from app.models import InventoryItem, StockMovement, StockMovementType


class InventoryNotFoundError(Exception):
    """Insumo inexistente no tenant atual."""


class InventoryConflictError(Exception):
    """Nome de insumo já utilizado."""


class InventoryValidationError(Exception):
    """Saldo ou movimentação inválida."""


async def list_items(session: AsyncSession) -> list[InventoryItem]:
    return list((await session.scalars(select(InventoryItem).order_by(InventoryItem.name))).all())


async def get_item(
    session: AsyncSession,
    item_id: UUID,
) -> InventoryItem:
    item = await session.get(InventoryItem, item_id)
    if item is None:
        raise InventoryNotFoundError
    return item


async def create_item(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    body: InventoryItemCreateRequest,
) -> InventoryItem:
    item = InventoryItem(
        id=uuid4(),
        tenant_id=tenant_id,
        name=body.name.strip(),
        unit=body.unit.strip(),
        quantity=body.quantity,
        min_quantity=body.min_quantity,
        unit_cost=body.unit_cost,
        is_active=body.is_active,
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise InventoryConflictError from exc
    return item


async def update_item(
    session: AsyncSession,
    *,
    item: InventoryItem,
    changes: dict[str, object],
) -> InventoryItem:
    for field in ("name", "unit", "min_quantity", "unit_cost", "is_active"):
        if field in changes:
            value = changes[field]
            if field == "name" and isinstance(value, str):
                value = value.strip()
            setattr(item, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise InventoryConflictError from exc
    return item


async def delete_item(
    session: AsyncSession,
    *,
    item: InventoryItem,
) -> None:
    await session.delete(item)
    await session.commit()


async def add_movement(
    session: AsyncSession,
    *,
    item: InventoryItem,
    actor_id: UUID,
    body: StockMovementCreateRequest,
) -> StockMovement:
    quantity = Decimal(body.quantity)
    if body.kind == StockMovementType.IN:
        item.quantity += quantity
    elif body.kind == StockMovementType.OUT:
        if quantity > item.quantity:
            raise InventoryValidationError("Saldo insuficiente para a saída")
        item.quantity -= quantity
    else:
        item.quantity = quantity

    movement = StockMovement(
        id=uuid4(),
        tenant_id=item.tenant_id,
        item_id=item.id,
        kind=body.kind.value,
        quantity=quantity,
        reason=body.reason.strip() if body.reason else None,
        document_type=(body.document_type.value if body.document_type else None),
        document_number=(body.document_number.strip() if body.document_number else None),
        document_series=(body.document_series.strip() if body.document_series else None),
        supplier_name=(body.supplier_name.strip() if body.supplier_name else None),
        supplier_tax_id=(body.supplier_tax_id.strip() if body.supplier_tax_id else None),
        issue_date=body.issue_date,
        total_amount=body.total_amount,
        payment_method=(body.payment_method.value if body.payment_method else None),
        access_key=body.access_key,
        created_by=actor_id,
    )
    session.add(movement)
    await session.commit()
    return movement


async def list_movements(
    session: AsyncSession,
    *,
    item: InventoryItem,
    limit: int = 50,
) -> list[StockMovement]:
    return list(
        (
            await session.scalars(
                select(StockMovement)
                .where(StockMovement.item_id == item.id)
                .order_by(StockMovement.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
