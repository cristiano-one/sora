"""Contratos públicos do link mágico (sem login)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.schemas.subscriptions import (
    PublicSubscriptionPlanResponse,
    PublicSubscriptionResponse,
)
from app.models import AppointmentStatus


class MagicLinkRequest(BaseModel):
    """Telefone validado pelo roteador determinístico do WhatsApp."""

    phone: str = Field(min_length=10, max_length=20)


class MagicLinkResponse(BaseModel):
    """Link e validade do token mágico."""

    url: str
    expires_in: int


class PublicServiceResponse(BaseModel):
    """Serviço visível no link público (sem dados internos)."""

    id: UUID
    name: str
    duration_minutes: int
    price: Decimal | None


class PublicProfessionalResponse(BaseModel):
    """Profissional visível no link público."""

    id: UUID
    full_name: str


class PublicContextResponse(BaseModel):
    """Contexto do link: clínica, serviços e profissionais."""

    tenant_name: str
    tenant_slug: str
    client_name: str | None
    services: list[PublicServiceResponse]
    professionals: list[PublicProfessionalResponse]
    plans: list[PublicSubscriptionPlanResponse]
    subscription: PublicSubscriptionResponse | None


class PublicAppointmentCreateRequest(BaseModel):
    """Agendamento feito pelo cliente final via link mágico."""

    service_id: UUID
    collaborator_id: UUID
    starts_at: datetime
    full_name: str = Field(min_length=2, max_length=255)


class PublicAppointmentResponse(BaseModel):
    """Retorno público do agendamento (sem score/bloqueio)."""

    id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    service_name: str
    collaborator_name: str
    deposit_amount: Decimal | None
