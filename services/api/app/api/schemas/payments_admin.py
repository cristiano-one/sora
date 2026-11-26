"""Contratos administrativos de cobranças Pix."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models import PaymentStatus


class AdminPaymentResponse(BaseModel):
    """Cobrança Pix visível para a gestão."""

    id: UUID
    client_id: UUID
    client_name: str
    appointment_id: UUID | None
    subscription_id: UUID | None
    amount: Decimal
    status: PaymentStatus
    provider: str
    expires_at: datetime
    paid_at: datetime | None
    created_at: datetime
