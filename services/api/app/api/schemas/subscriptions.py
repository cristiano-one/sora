"""Contratos de assinaturas de clientes e cotas de serviço."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.schemas.payments import PublicPaymentResponse
from app.models import BillingCycle, ClientSubscriptionStatus


class SubscriptionQuotaResponse(BaseModel):
    """Cota de um serviço no ciclo atual da assinatura."""

    service_id: UUID
    service_name: str
    uses_per_cycle: int
    used: int
    remaining: int
    min_interval_days: int | None
    allowed_weekdays: list[int] | None


class ClientSubscriptionResponse(BaseModel):
    """Assinatura para o painel interno."""

    id: UUID
    client_id: UUID
    client_name: str
    plan_id: UUID
    plan_name: str
    status: ClientSubscriptionStatus
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    quotas: list[SubscriptionQuotaResponse]


class ClientSubscriptionCreateRequest(BaseModel):
    """Contratação manual de plano pelo painel."""

    plan_id: UUID


class PublicSubscriptionPlanItemResponse(BaseModel):
    """Serviço e cota incluídos em um plano público."""

    service_id: UUID
    service_name: str
    uses_per_cycle: int
    min_interval_days: int | None
    allowed_weekdays: list[int] | None


class PublicSubscriptionPlanResponse(BaseModel):
    """Plano de assinatura visível no link público."""

    id: UUID
    name: str
    description: str | None
    price: Decimal
    billing_cycle: BillingCycle
    items: list[PublicSubscriptionPlanItemResponse]


class PublicSubscriptionResponse(BaseModel):
    """Assinatura ativa do cliente dono do link mágico."""

    status: ClientSubscriptionStatus
    plan_id: UUID
    plan_name: str
    current_period_start: datetime
    current_period_end: datetime
    quotas: list[SubscriptionQuotaResponse]
    payment: PublicPaymentResponse | None = None


class PublicSubscriptionCreateRequest(BaseModel):
    """Contratação de plano pelo cliente final."""

    plan_id: UUID
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
