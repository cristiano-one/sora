"""Endpoints financeiros: contas, lançamentos, caixa, DRE e exportação."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.finance import (
    AccountBalanceResponse,
    CashFlowResponse,
    CommissionSummaryResponse,
    DreResponse,
    FinancialAccountCreateRequest,
    FinancialAccountResponse,
    FinancialAccountUpdateRequest,
    FinancialEntryCreateRequest,
    FinancialEntryResponse,
    FinancialEntryUpdateRequest,
    SalesResponse,
    TitheDeliveryCreateRequest,
    TitheDeliveryResponse,
    TitheSummaryResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_current_principal,
    get_tenant_session,
    require_roles,
)
from app.models import FinancialEntryStatus, TitheDelivery, UserRole
from app.modules.finance.service import (
    FinanceConflictError,
    FinanceInUseError,
    FinanceNotFoundError,
    FinanceValidationError,
    account_balances,
    cash_flow,
    commission_summary,
    create_account,
    create_entry,
    create_tithe_delivery,
    delete_account,
    delete_entry,
    delete_tithe_delivery,
    dre,
    export_csv,
    get_account,
    get_entry,
    list_accounts,
    list_entries,
    list_tithe_deliveries,
    sales,
    update_account,
    update_entry,
)

router = APIRouter(prefix="/finance", tags=["finance"])

_require_owner = require_roles(UserRole.OWNER)


def _period(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo de datas inválido",
        )
    if (to_date - from_date).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo máximo de 366 dias",
        )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FinanceNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro financeiro não encontrado",
        )
    if isinstance(exc, FinanceConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de conta já utilizado",
        )
    if isinstance(exc, FinanceInUseError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conta possui lançamentos e não pode ser excluída",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@router.get(
    "/accounts",
    response_model=list[FinancialAccountResponse],
    summary="Lista contas/caixas",
)
async def list_accounts_endpoint(
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[FinancialAccountResponse]:
    return await list_accounts(session)


@router.post(
    "/accounts",
    response_model=FinancialAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra conta/caixa",
)
async def create_account_endpoint(
    body: FinancialAccountCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> FinancialAccountResponse:
    try:
        account = await create_account(
            session,
            tenant_id=principal.tenant_id,
            name=body.name,
            account_type=body.type,
            initial_balance=body.initial_balance,
        )
    except FinanceConflictError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.account.create",
        resource_type="financial_account",
        resource_id=account.id,
        ip_address=client_ip(request),
    )
    return account


@router.patch(
    "/accounts/{account_id}",
    response_model=FinancialAccountResponse,
    summary="Atualiza conta/caixa",
)
async def update_account_endpoint(
    account_id: UUID,
    body: FinancialAccountUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> FinancialAccountResponse:
    try:
        account = await get_account(session, account_id)
        updated = await update_account(
            session,
            account=account,
            changes=body.model_dump(exclude_unset=True),
        )
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.account.update",
        resource_type="financial_account",
        resource_id=updated.id,
        ip_address=client_ip(request),
    )
    return updated


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui conta/caixa sem lançamentos",
)
async def delete_account_endpoint(
    account_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    try:
        account = await get_account(session, account_id)
        await delete_account(session, account=account)
    except FinanceNotFoundError as exc:
        raise _map_error(exc) from exc
    except FinanceInUseError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.account.delete",
        resource_type="financial_account",
        resource_id=account_id,
        ip_address=client_ip(request),
    )


@router.get(
    "/accounts/balances",
    response_model=list[AccountBalanceResponse],
    summary="Saldo atual por conta/caixa",
)
async def account_balances_endpoint(
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AccountBalanceResponse]:
    return await account_balances(session)


@router.get(
    "/entries",
    response_model=list[FinancialEntryResponse],
    summary="Lista lançamentos por competência",
)
async def list_entries_endpoint(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    entry_status: FinancialEntryStatus | None = Query(
        default=None,
        alias="status",
    ),
    account_id: UUID | None = Query(default=None),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[FinancialEntryResponse]:
    if from_date is not None and to_date is not None:
        _period(from_date, to_date)
    return await list_entries(
        session,
        from_date=from_date,
        to_date=to_date,
        entry_status=entry_status,
        account_id=account_id,
    )


@router.post(
    "/entries",
    response_model=FinancialEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria lançamento financeiro",
)
async def create_entry_endpoint(
    body: FinancialEntryCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> FinancialEntryResponse:
    try:
        entry = await create_entry(
            session,
            tenant_id=principal.tenant_id,
            created_by=principal.user_id,
            body=body,
        )
    except (FinanceNotFoundError, FinanceValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.entry.create",
        resource_type="financial_entry",
        resource_id=entry.id,
        ip_address=client_ip(request),
    )
    return entry


@router.patch(
    "/entries/{entry_id}",
    response_model=FinancialEntryResponse,
    summary="Atualiza lançamento financeiro",
)
async def update_entry_endpoint(
    entry_id: UUID,
    body: FinancialEntryUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> FinancialEntryResponse:
    try:
        entry = await get_entry(session, entry_id)
        updated = await update_entry(
            session,
            entry=entry,
            changes=body.model_dump(exclude_unset=True),
        )
    except (FinanceNotFoundError, FinanceValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.entry.update",
        resource_type="financial_entry",
        resource_id=updated.id,
        ip_address=client_ip(request),
    )
    return updated


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui lançamento financeiro",
)
async def delete_entry_endpoint(
    entry_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    try:
        entry = await get_entry(session, entry_id)
        await delete_entry(session, entry=entry)
    except FinanceNotFoundError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.entry.delete",
        resource_type="financial_entry",
        resource_id=entry_id,
        ip_address=client_ip(request),
    )


@router.get(
    "/cash-flow",
    response_model=CashFlowResponse,
    summary="Fluxo de caixa realizado",
)
async def cash_flow_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> CashFlowResponse:
    _period(from_date, to_date)
    return await cash_flow(session, from_date=from_date, to_date=to_date)


@router.get(
    "/dre",
    response_model=DreResponse,
    summary="DRE simplificada por competência",
)
async def dre_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> DreResponse:
    _period(from_date, to_date)
    return await dre(
        session,
        tenant_id=principal.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/commissions",
    response_model=CommissionSummaryResponse,
    summary="Comissões apuradas por colaborador",
)
async def commissions_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> CommissionSummaryResponse:
    _period(from_date, to_date)
    return await commission_summary(
        session,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/my-commission",
    response_model=CommissionSummaryResponse,
    summary="Comissão do próprio usuário (todos os papéis)",
)
async def my_commission_summary_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> CommissionSummaryResponse:
    _period(from_date, to_date)
    return await commission_summary(
        session,
        from_date=from_date,
        to_date=to_date,
        collaborator_id=principal.user_id,
    )


@router.get(
    "/sales",
    response_model=SalesResponse,
    summary="Valor líquido por atendimento concluído",
)
async def sales_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> SalesResponse:
    _period(from_date, to_date)
    return await sales(session, from_date=from_date, to_date=to_date)


@router.get(
    "/export",
    summary="Exporta lançamentos em CSV (OWNER)",
)
async def export_endpoint(
    request: Request,
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    _period(from_date, to_date)
    csv_content = await export_csv(
        session,
        from_date=from_date,
        to_date=to_date,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.export",
        resource_type="financial_entry",
        resource_id=None,
        ip_address=client_ip(request),
        details={"from_date": from_date.isoformat(), "to_date": to_date.isoformat()},
    )
    filename = f"sora-financeiro-{from_date}-{to_date}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _tithe_delivery_response(delivery: TitheDelivery) -> TitheDeliveryResponse:
    return TitheDeliveryResponse(
        id=delivery.id,
        competence_date=delivery.competence_date,
        tithe_amount=delivery.tithe_amount,
        offering_amount=delivery.offering_amount,
        note=delivery.note,
        created_at=delivery.created_at,
    )


@router.get(
    "/tithe",
    response_model=TitheSummaryResponse,
    summary="Provisão de dízimo/oferta e entregas do período",
)
async def tithe_summary_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> TitheSummaryResponse:
    _period(from_date, to_date)
    dre_data = await dre(
        session,
        tenant_id=principal.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )
    deliveries = await list_tithe_deliveries(
        session,
        from_date=from_date,
        to_date=to_date,
    )
    delivered_tithe = sum(
        (item.tithe_amount for item in deliveries),
        Decimal("0.00"),
    )
    delivered_offering = sum(
        (item.offering_amount for item in deliveries),
        Decimal("0.00"),
    )
    return TitheSummaryResponse(
        dre=dre_data,
        deliveries=[_tithe_delivery_response(item) for item in deliveries],
        delivered_tithe=delivered_tithe,
        delivered_offering=delivered_offering,
        pending_tithe=max(
            dre_data.tithe_amount - delivered_tithe,
            Decimal("0.00"),
        ),
        pending_offering=max(
            dre_data.offering_amount - delivered_offering,
            Decimal("0.00"),
        ),
    )


@router.post(
    "/tithe/deliveries",
    response_model=TitheDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra entrega de dízimo/oferta",
)
async def create_tithe_delivery_endpoint(
    body: TitheDeliveryCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> TitheDeliveryResponse:
    try:
        delivery = await create_tithe_delivery(
            session,
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            body=body,
        )
    except FinanceValidationError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.tithe_delivery",
        resource_type="tithe_delivery",
        resource_id=delivery.id,
        ip_address=client_ip(request),
        details={
            "tithe_amount": str(delivery.tithe_amount),
            "offering_amount": str(delivery.offering_amount),
        },
    )
    return _tithe_delivery_response(delivery)


@router.delete(
    "/tithe/deliveries/{delivery_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui uma entrega de dízimo/oferta",
)
async def delete_tithe_delivery_endpoint(
    delivery_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    delivery = await session.get(TitheDelivery, delivery_id)
    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega não encontrada",
        )
    await delete_tithe_delivery(session, delivery)
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="finance.tithe_delivery.delete",
        resource_type="tithe_delivery",
        resource_id=delivery_id,
        ip_address=client_ip(request),
    )
