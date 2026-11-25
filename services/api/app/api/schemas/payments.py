"""Contratos públicos de pagamento Pix."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models import AppointmentStatus, ClientSubscriptionStatus, PaymentStatus


class PublicPaymentResponse(BaseModel):
    """Cobrança Pix visível para o cliente dono do link."""

    id: UUID
    amount: Decimal
    status: PaymentStatus
    pix_copy_paste: str
    qr_code_data_uri: str
    expires_at: datetime


class PublicPaymentConfirmResponse(PublicPaymentResponse):
    """Resultado da confirmação mock do Pix."""

    appointment_status: AppointmentStatus | None = None
    subscription_status: ClientSubscriptionStatus | None = None
