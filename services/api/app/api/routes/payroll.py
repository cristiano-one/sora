"""Endpoints de folha de pagamento e pró-labore."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.payroll import (
    PayrollEntryCreateRequest,
    PayrollEntryResponse,
    PayrollEntryUpdateRequest,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.models import PayrollEntry, PayrollKind, User, UserRole
from app.modules.payroll.service import (
    PayrollNotFoundError,
    PayrollValidationError,
    create_payroll_entry,
    delete_payroll_entry,
    get_payroll_entry,
    list_payroll,
    update_payroll_entry,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])

_require_owner = require_roles(UserRole.OWNER)


def _response(entry: PayrollEntry, user_name: str) -> PayrollEntryResponse:
    return PayrollEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        user_name=user_name,
        kind=PayrollKind(entry.kind),
        description=entry.description,
        amount=entry.amount,
        competence_date=entry.competence_date,
        status=entry.status,
        cash_date=entry.cash_date,
        financial_entry_id=entry.financial_entry_id,
        created_at=entry.created_at,
    )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PayrollNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verba de folha não encontrada",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@router.get(
    "",
    response_model=list[PayrollEntryResponse],
    summary="Lista verbas de folha no período",
)
async def list_payroll_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    user_id: UUID | None = Query(default=None),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[PayrollEntryResponse]:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo de datas inválido",
        )
    rows = await list_payroll(
        session,
        from_date=from_date,
        to_date=to_date,
        user_id=user_id,
    )
    return [_response(entry, name) for entry, name in rows]


@router.post(
    "",
    response_model=PayrollEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra verba de folha",
)
async def create_payroll_endpoint(
    body: PayrollEntryCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> PayrollEntryResponse:
    try:
        entry = await create_payroll_entry(
            session,
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            body=body,
        )
        user = await session.get(User, entry.user_id)
    except PayrollValidationError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="payroll.create",
        resource_type="payroll_entry",
        resource_id=entry.id,
        ip_address=client_ip(request),
        details={"kind": entry.kind, "status": entry.status.value},
    )
    return _response(entry, user.full_name if user else "Usuário")


@router.patch(
    "/{entry_id}",
    response_model=PayrollEntryResponse,
    summary="Atualiza verba de folha",
)
async def update_payroll_endpoint(
    entry_id: UUID,
    body: PayrollEntryUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> PayrollEntryResponse:
    try:
        entry = await get_payroll_entry(session, entry_id)
        entry = await update_payroll_entry(
            session,
            entry=entry,
            actor_id=principal.user_id,
            body=body,
        )
        user = await session.get(User, entry.user_id)
    except (PayrollNotFoundError, PayrollValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="payroll.update",
        resource_type="payroll_entry",
        resource_id=entry.id,
        ip_address=client_ip(request),
    )
    return _response(entry, user.full_name if user else "Usuário")


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui verba de folha e lançamento vinculado",
)
async def delete_payroll_endpoint(
    entry_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    try:
        entry = await get_payroll_entry(session, entry_id)
        await delete_payroll_entry(session, entry=entry)
    except PayrollNotFoundError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="payroll.delete",
        resource_type="payroll_entry",
        resource_id=entry_id,
        ip_address=client_ip(request),
    )
