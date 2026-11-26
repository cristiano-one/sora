"""Endpoints da comanda digital."""

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.fiscal import FiscalInvoiceResponse
from app.api.schemas.sales import (
    SaleAccountResponse,
    SaleCloseRequest,
    SaleCreditRequest,
    SaleItemCreateRequest,
    SaleItemResponse,
    SaleResponse,
    SaleUpdateRequest,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.core.config import settings
from app.models import (
    FinancialAccount,
    FiscalInvoice,
    Sale,
    SaleStatus,
    User,
    UserRole,
)
from app.modules.fiscal.service import (
    FiscalValidationError,
    cancel_invoice,
    get_invoice,
    issue_invoice,
)
from app.modules.sales.service import (
    SaleNotFoundError,
    SaleValidationError,
    add_item,
    apply_credit,
    cancel_sale,
    close_sale,
    create_from_appointment,
    get_sale,
    list_sales,
    remove_item,
    update_sale,
)

router = APIRouter(prefix="/sales", tags=["sales"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


def _today() -> date:
    return datetime.now(ZoneInfo(settings.default_tenant_timezone)).date()


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SaleNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comanda não encontrada",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


async def _response(
    session: AsyncSession,
    sale: Sale,
) -> SaleResponse:
    collaborator_name = None
    if sale.collaborator_id is not None:
        user = await session.get(User, sale.collaborator_id)
        collaborator_name = user.full_name if user else None
    return SaleResponse(
        id=sale.id,
        client_id=sale.client_id,
        client_name=sale.client.full_name,
        appointment_id=sale.appointment_id,
        collaborator_id=sale.collaborator_id,
        collaborator_name=collaborator_name,
        status=sale.status,
        subtotal=sale.subtotal,
        discount=sale.discount,
        credit_amount=sale.credit_amount,
        total=sale.total,
        payment_method=sale.payment_method,
        account_id=sale.account_id,
        financial_entry_id=sale.financial_entry_id,
        notes=sale.notes,
        created_at=sale.created_at,
        closed_at=sale.closed_at,
        items=[
            SaleItemResponse(
                id=item.id,
                service_id=item.service_id,
                inventory_item_id=item.inventory_item_id,
                category=item.category,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                cost=item.cost,
                total=item.total,
            )
            for item in sale.items
        ],
    )


@router.get(
    "/accounts",
    response_model=list[SaleAccountResponse],
    summary="Contas disponíveis para fechar a comanda",
)
async def sale_accounts_endpoint(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[SaleAccountResponse]:
    accounts = (
        await session.scalars(
            select(FinancialAccount)
            .where(FinancialAccount.is_active.is_(True))
            .order_by(FinancialAccount.name)
        )
    ).all()
    return [
        SaleAccountResponse(
            id=account.id,
            name=account.name,
            type=account.type.value,
        )
        for account in accounts
    ]


@router.post(
    "/from-appointment/{appointment_id}",
    response_model=SaleResponse,
    summary="Abre (ou recupera) a comanda de um agendamento",
)
async def create_from_appointment_endpoint(
    appointment_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await create_from_appointment(
            session,
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            appointment_id=appointment_id,
        )
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.open",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
        details={"appointment_id": str(appointment_id)},
    )
    return await _response(session, sale)


@router.get(
    "",
    response_model=list[SaleResponse],
    summary="Lista comandas no período",
)
async def list_sales_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    sale_status: SaleStatus | None = Query(default=None, alias="status"),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[SaleResponse]:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo de datas inválido",
        )
    sales = await list_sales(
        session,
        from_date=from_date,
        to_date=to_date,
        status=sale_status,
    )
    return [await _response(session, sale) for sale in sales]


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Detalha uma comanda",
)
async def get_sale_endpoint(
    sale_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
    except SaleNotFoundError as exc:
        raise _map_error(exc) from exc
    return await _response(session, sale)


@router.post(
    "/{sale_id}/items",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona item à comanda",
)
async def add_item_endpoint(
    sale_id: UUID,
    body: SaleItemCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await add_item(
            session,
            sale=sale,
            tenant_id=principal.tenant_id,
            body=body,
        )
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.item.add",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
    )
    return await _response(session, sale)


@router.delete(
    "/{sale_id}/items/{item_id}",
    response_model=SaleResponse,
    summary="Remove item da comanda",
)
async def remove_item_endpoint(
    sale_id: UUID,
    item_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await remove_item(session, sale=sale, item_id=item_id)
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.item.remove",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
    )
    return await _response(session, sale)


@router.patch(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Atualiza desconto/observações da comanda",
)
async def update_sale_endpoint(
    sale_id: UUID,
    body: SaleUpdateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await update_sale(session, sale=sale, body=body)
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    return await _response(session, sale)


@router.post(
    "/{sale_id}/credits",
    response_model=SaleResponse,
    summary="Aplica crédito do cliente na comanda",
)
async def apply_credit_endpoint(
    sale_id: UUID,
    body: SaleCreditRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await apply_credit(
            session,
            sale=sale,
            actor_id=principal.user_id,
            body=body,
            today=_today(),
        )
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.credit.apply",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
        details={"amount": str(body.amount)},
    )
    return await _response(session, sale)


@router.post(
    "/{sale_id}/close",
    response_model=SaleResponse,
    summary="Fecha a comanda e integra ao financeiro",
)
async def close_sale_endpoint(
    sale_id: UUID,
    body: SaleCloseRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await close_sale(
            session,
            sale=sale,
            actor_id=principal.user_id,
            body=body,
            today=_today(),
        )
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.close",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
        details={
            "total": str(sale.total),
            "payment_method": sale.payment_method.value
            if sale.payment_method
            else None,
        },
    )
    return await _response(session, sale)


@router.post(
    "/{sale_id}/cancel",
    response_model=SaleResponse,
    summary="Cancela uma comanda aberta e devolve créditos",
)
async def cancel_sale_endpoint(
    sale_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SaleResponse:
    try:
        sale = await get_sale(session, sale_id)
        sale = await cancel_sale(session, sale=sale)
    except (SaleNotFoundError, SaleValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="sale.cancel",
        resource_type="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
    )
    return await _response(session, sale)


def _invoice_response(invoice: FiscalInvoice) -> FiscalInvoiceResponse:
    return FiscalInvoiceResponse(
        id=invoice.id,
        sale_id=invoice.sale_id,
        status=invoice.status,
        number=invoice.number,
        provider=invoice.provider,
        amount=invoice.amount,
        issued_at=invoice.issued_at,
        cancelled_at=invoice.cancelled_at,
    )


@router.get(
    "/{sale_id}/invoice",
    response_model=FiscalInvoiceResponse,
    summary="Consulta a NFS-e da comanda",
)
async def get_invoice_endpoint(
    sale_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> FiscalInvoiceResponse:
    invoice = await get_invoice(session, sale_id=sale_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada",
        )
    return _invoice_response(invoice)


@router.post(
    "/{sale_id}/invoice",
    response_model=FiscalInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Emite NFS-e da comanda (adapter mock)",
)
async def issue_invoice_endpoint(
    sale_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> FiscalInvoiceResponse:
    try:
        sale = await get_sale(session, sale_id)
        invoice = await issue_invoice(session, sale=sale)
    except (SaleNotFoundError, FiscalValidationError) as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="fiscal.invoice.issue",
        resource_type="fiscal_invoice",
        resource_id=invoice.id,
        ip_address=client_ip(request),
        details={"number": invoice.number, "amount": str(invoice.amount)},
    )
    return _invoice_response(invoice)


@router.post(
    "/{sale_id}/invoice/cancel",
    response_model=FiscalInvoiceResponse,
    summary="Cancela a NFS-e da comanda",
)
async def cancel_invoice_endpoint(
    sale_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> FiscalInvoiceResponse:
    invoice = await get_invoice(session, sale_id=sale_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada",
        )
    try:
        invoice = await cancel_invoice(session, invoice=invoice)
    except FiscalValidationError as exc:
        raise _map_error(exc) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="fiscal.invoice.cancel",
        resource_type="fiscal_invoice",
        resource_id=invoice.id,
        ip_address=client_ip(request),
    )
    return _invoice_response(invoice)
