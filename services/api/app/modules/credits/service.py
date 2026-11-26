"""Regras de créditos promocionais de clientes."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.clients import ClientCreditUsageCreateRequest
from app.models import Appointment, ClientCredit, ClientCreditUsage


class ClientCreditNotFoundError(Exception):
    """Crédito inexistente no cliente/tenant."""


class ClientCreditValidationError(Exception):
    """Crédito expirado, sem saldo ou vínculo inválido."""


def remaining_amount(credit: ClientCredit) -> Decimal:
    return max(credit.amount - credit.used_amount, Decimal("0.00"))


async def list_credits(
    session: AsyncSession,
    *,
    client_id: UUID,
) -> list[ClientCredit]:
    return list(
        (
            await session.scalars(
                select(ClientCredit)
                .where(ClientCredit.client_id == client_id)
                .order_by(ClientCredit.expires_at.desc())
            )
        ).all()
    )


async def list_usages(
    session: AsyncSession,
    *,
    client_id: UUID,
) -> list[ClientCreditUsage]:
    return list(
        (
            await session.scalars(
                select(ClientCreditUsage)
                .where(ClientCreditUsage.client_id == client_id)
                .order_by(ClientCreditUsage.created_at.desc())
                .limit(100)
            )
        ).all()
    )


async def use_credit(
    session: AsyncSession,
    *,
    credit: ClientCredit,
    actor_id: UUID,
    body: ClientCreditUsageCreateRequest,
    today: date,
) -> ClientCreditUsage:
    if credit.expires_at < today:
        raise ClientCreditValidationError("Crédito expirado")
    remaining = remaining_amount(credit)
    if body.amount > remaining:
        raise ClientCreditValidationError(
            "Valor acima do saldo disponível do crédito"
        )
    if body.appointment_id is not None:
        appointment = await session.get(Appointment, body.appointment_id)
        if appointment is None or appointment.client_id != credit.client_id:
            raise ClientCreditValidationError(
                "Agendamento não pertence a este cliente"
            )

    credit.used_amount += body.amount
    usage = ClientCreditUsage(
        id=uuid4(),
        tenant_id=credit.tenant_id,
        credit_id=credit.id,
        client_id=credit.client_id,
        appointment_id=body.appointment_id,
        amount=body.amount,
        note=body.note.strip() if body.note else None,
        created_by=actor_id,
    )
    session.add(usage)
    await session.commit()
    return usage
