"""Endpoints de estoque de insumos."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.inventory import (
    InventoryItemCreateRequest,
    InventoryItemResponse,
    InventoryItemUpdateRequest,
    StockMovementCreateRequest,
    StockMovementResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.models import InventoryItem, StockMovement, UserRole
from app.modules.inventory.service import (
    InventoryConflictError,
    InventoryNotFoundError,
    InventoryValidationError,
    add_movement,
    create_item,
    delete_item,
    get_item,
    list_items,
    list_movements,
    update_item,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)
_CENT = Decimal("0.01")


def _item_response(item: InventoryItem) -> InventoryItemResponse:
    return InventoryItemResponse(
        id=item.id,
        name=item.name,
        unit=item.unit,
        quantity=item.quantity,
        min_quantity=item.min_quantity,
        unit_cost=item.unit_cost,
        is_active=item.is_active,
        low_stock=item.min_quantity > 0 and item.quantity <= item.min_quantity,
        total_value=(item.quantity * item.unit_cost).quantize(_CENT),
        created_at=item.created_at,
    )


def _movement_response(movement: StockMovement) -> StockMovementResponse:
    return StockMovementResponse(
        id=movement.id,
        item_id=movement.item_id,
        kind=movement.kind,
        quantity=movement.quantity,
        reason=movement.reason,
        document_type=movement.document_type,
        document_number=movement.document_number,
        document_series=movement.document_series,
        supplier_name=movement.supplier_name,
        supplier_tax_id=movement.supplier_tax_id,
        issue_date=movement.issue_date,
        total_amount=movement.total_amount,
        payment_method=movement.payment_method,
        access_key=movement.access_key,
        created_at=movement.created_at,
    )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InventoryNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insumo não encontrado",
        )
    if isinstance(exc, InventoryConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um insumo com este nome",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@router.get(
    "",
    response_model=list[InventoryItemResponse],
    summary="Lista insumos e saldos",
)
async def list_items_endpoint(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[InventoryItemResponse]:
    return [_item_response(item) for item in await list_items(session)]


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra insumo",
)
async def create_item_endpoint(
    body: InventoryItemCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> InventoryItemResponse:
    try:
        item = await create_item(
            session,
            tenant_id=principal.tenant_id,
            body=body,
        )
    except InventoryConflictError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="inventory.create",
        resource_type="inventory_item",
        resource_id=item.id,
        ip_address=client_ip(request),
        details={"name": item.name},
    )
    return _item_response(item)


@router.patch(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Atualiza insumo",
)
async def update_item_endpoint(
    item_id: UUID,
    body: InventoryItemUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> InventoryItemResponse:
    try:
        item = await get_item(session, item_id)
        item = await update_item(
            session,
            item=item,
            changes=body.model_dump(exclude_unset=True),
        )
    except (InventoryNotFoundError, InventoryConflictError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="inventory.update",
        resource_type="inventory_item",
        resource_id=item.id,
        ip_address=client_ip(request),
    )
    return _item_response(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui insumo",
)
async def delete_item_endpoint(
    item_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    try:
        item = await get_item(session, item_id)
        await delete_item(session, item=item)
    except InventoryNotFoundError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="inventory.delete",
        resource_type="inventory_item",
        resource_id=item_id,
        ip_address=client_ip(request),
    )


@router.post(
    "/{item_id}/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra entrada, saída ou ajuste de estoque",
)
async def create_movement_endpoint(
    item_id: UUID,
    body: StockMovementCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> StockMovementResponse:
    try:
        item = await get_item(session, item_id)
        movement = await add_movement(
            session,
            item=item,
            actor_id=principal.user_id,
            body=body,
        )
    except (InventoryNotFoundError, InventoryValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="inventory.movement",
        resource_type="inventory_item",
        resource_id=item.id,
        ip_address=client_ip(request),
        details={
            "kind": movement.kind,
            "quantity": str(movement.quantity),
            "document_type": movement.document_type,
            "document_number": movement.document_number,
        },
    )
    return _movement_response(movement)


@router.get(
    "/{item_id}/movements",
    response_model=list[StockMovementResponse],
    summary="Lista movimentações de um insumo",
)
async def list_movements_endpoint(
    item_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[StockMovementResponse]:
    try:
        item = await get_item(session, item_id)
    except InventoryNotFoundError as exc:
        raise _map_error(exc) from exc
    movements = await list_movements(session, item=item, limit=limit)
    return [_movement_response(movement) for movement in movements]
