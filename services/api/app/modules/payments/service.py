"""Ciclo de vida dos pagamentos Pix e geração de QR."""

import base64
import io
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import segno
from app.api.schemas.payments import PublicPaymentResponse
from app.models import (
    Appointment,
    AppointmentStatus,
    ClientSubscription,
    ClientSubscriptionStatus,
    PaymentIntent,
    PaymentStatus,
)
from app.modules.payments.providers import get_payment_provider
from app.modules.subscriptions.service import period_end
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def qr_code_data_uri(payload: str) -> str:
    """Gera um PNG do BR Code como data URI (sem serviço externo)."""
    qr = segno.make(payload, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=6, border=2)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def payment_response(payment: PaymentIntent) -> PublicPaymentResponse:
    return PublicPaymentResponse(
        id=payment.id,
        amount=payment.amount,
        status=payment.status,
        pix_copy_paste=payment.pix_payload,
        qr_code_data_uri=qr_code_data_uri(payment.pix_payload),
        expires_at=payment.expires_at,
    )


async def create_payment_intent(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    client_id: UUID,
    amount: Decimal,
    expires_at: datetime,
    appointment_id: UUID | None = None,
    subscription_id: UUID | None = None,
) -> PaymentIntent:
    """Cria a cobrança Pix pendente (commit fica com o chamador)."""
    if amount <= 0:
        raise ValueError("amount deve ser positivo")
    reference = appointment_id or subscription_id or uuid4()
    provider = get_payment_provider()
    charge = provider.create_pix_charge(
        amount=amount,
        txid=reference,
        description="Sinal/assinatura Sora Studio",
    )
    payment = PaymentIntent(
        tenant_id=tenant_id,
        client_id=client_id,
        appointment_id=appointment_id,
        subscription_id=subscription_id,
        amount=amount,
        status=PaymentStatus.PENDING,
        provider=charge.provider,
        pix_payload=charge.payload,
        expires_at=expires_at,
    )
    session.add(payment)
    return payment


async def get_payment(
    session: AsyncSession,
    payment_id: UUID,
) -> PaymentIntent | None:
    return await session.get(PaymentIntent, payment_id)


async def get_payment_for_appointment(
    session: AsyncSession,
    appointment_id: UUID,
) -> PaymentIntent | None:
    return await session.scalar(
        select(PaymentIntent)
        .where(PaymentIntent.appointment_id == appointment_id)
        .order_by(PaymentIntent.created_at.desc())
        .limit(1)
    )


async def get_payment_for_subscription(
    session: AsyncSession,
    subscription_id: UUID,
) -> PaymentIntent | None:
    return await session.scalar(
        select(PaymentIntent)
        .where(PaymentIntent.subscription_id == subscription_id)
        .order_by(PaymentIntent.created_at.desc())
        .limit(1)
    )


def _activate_subscription(
    subscription: ClientSubscription,
    now: datetime,
) -> None:
    subscription.status = ClientSubscriptionStatus.ACTIVE
    subscription.started_at = now
    subscription.current_period_start = now
    subscription.current_period_end = period_end(subscription.plan, now)


async def confirm_payment(
    session: AsyncSession,
    payment: PaymentIntent,
    *,
    now: datetime | None = None,
) -> tuple[Appointment | None, ClientSubscription | None]:
    """Marca pago, confirma o agendamento e ativa a assinatura."""
    moment = now or datetime.now(UTC)
    payment.status = PaymentStatus.PAID
    payment.paid_at = moment

    appointment: Appointment | None = None
    if payment.appointment_id is not None:
        appointment = await session.get(Appointment, payment.appointment_id)
        if (
            appointment is not None
            and appointment.status == AppointmentStatus.PENDING_DEPOSIT
        ):
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.deposit_expires_at = None

    subscription: ClientSubscription | None = None
    if payment.subscription_id is not None:
        subscription = await session.get(
            ClientSubscription,
            payment.subscription_id,
        )
        if (
            subscription is not None
            and subscription.status == ClientSubscriptionStatus.PENDING_PAYMENT
        ):
            _activate_subscription(subscription, moment)
    return appointment, subscription


async def expire_payment(
    session: AsyncSession,
    payment: PaymentIntent,
) -> tuple[Appointment | None, ClientSubscription | None]:
    """Expira a cobrança e libera reserva/assinatura pendentes."""
    payment.status = PaymentStatus.EXPIRED
    appointment: Appointment | None = None
    if payment.appointment_id is not None:
        appointment = await session.get(Appointment, payment.appointment_id)
        if (
            appointment is not None
            and appointment.status == AppointmentStatus.PENDING_DEPOSIT
        ):
            appointment.status = AppointmentStatus.EXPIRED
            appointment.deposit_expires_at = None

    subscription: ClientSubscription | None = None
    if payment.subscription_id is not None:
        subscription = await session.get(
            ClientSubscription,
            payment.subscription_id,
        )
        if (
            subscription is not None
            and subscription.status == ClientSubscriptionStatus.PENDING_PAYMENT
        ):
            subscription.status = ClientSubscriptionStatus.EXPIRED
    return appointment, subscription


async def cancel_pending_payments(
    session: AsyncSession,
    *,
    appointment_id: UUID,
) -> None:
    payments = (
        await session.scalars(
            select(PaymentIntent).where(
                PaymentIntent.appointment_id == appointment_id,
                PaymentIntent.status == PaymentStatus.PENDING,
            )
        )
    ).all()
    for payment in payments:
        payment.status = PaymentStatus.CANCELLED


async def expire_pending_payments(
    session: AsyncSession,
    *,
    appointment_ids: list[UUID],
) -> None:
    if not appointment_ids:
        return
    payments = (
        await session.scalars(
            select(PaymentIntent).where(
                PaymentIntent.appointment_id.in_(appointment_ids),
                PaymentIntent.status == PaymentStatus.PENDING,
            )
        )
    ).all()
    for payment in payments:
        payment.status = PaymentStatus.EXPIRED
