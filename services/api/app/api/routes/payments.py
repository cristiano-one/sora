"""Painel administrativo de cobranças Pix."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.payments_admin import AdminPaymentResponse
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.models import Client, PaymentIntent, PaymentStatus, UserRole
from app.modules.payments.service import (
    confirm_payment,
    get_payment,
    list_payment_intents,
)

router = APIRouter(prefix="/payments", tags=["payments"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


def _response(payment: PaymentIntent, client_name: str) -> AdminPaymentResponse:
    return AdminPaymentResponse(
        id=payment.id,
        client_id=payment.client_id,
        client_name=client_name,
        appointment_id=payment.appointment_id,
        subscription_id=payment.subscription_id,
        amount=payment.amount,
        status=payment.status,
        provider=payment.provider,
        expires_at=payment.expires_at,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


@router.get(
    "",
    response_model=list[AdminPaymentResponse],
    summary="Lista cobranças Pix da clínica",
)
async def list_payments_endpoint(
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AdminPaymentResponse]:
    rows = await list_payment_intents(
        session,
        status=payment_status,
        limit=limit,
    )
    return [_response(payment, name) for payment, name in rows]


@router.post(
    "/{payment_id}/confirm",
    response_model=AdminPaymentResponse,
    summary="Confirma manualmente um Pix pendente",
)
async def confirm_payment_endpoint(
    payment_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AdminPaymentResponse:
    payment = await get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cobrança não encontrada",
        )
    if payment.status == PaymentStatus.PAID:
        client = await session.get(Client, payment.client_id)
        return _response(payment, client.full_name if client else "Cliente")
    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cobrança não está pendente",
        )

    await confirm_payment(session, payment)
    await session.commit()
    client = await session.get(Client, payment.client_id)
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="payment.confirm_manual",
        resource_type="payment",
        resource_id=payment.id,
        ip_address=client_ip(request),
        details={
            "appointment_id": str(payment.appointment_id)
            if payment.appointment_id
            else None,
            "subscription_id": str(payment.subscription_id)
            if payment.subscription_id
            else None,
        },
    )
    return _response(payment, client.full_name if client else "Cliente")
