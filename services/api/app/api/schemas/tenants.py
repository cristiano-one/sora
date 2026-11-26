"""Contratos do módulo de tenants."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import BusinessProfile, TaxRegime, UserRole


class CurrentTenantResponse(BaseModel):
    """Dados públicos do tenant atual."""

    id: UUID
    name: str
    slug: str
    tax_regime: TaxRegime
    business_profile: BusinessProfile


class TenantCreateRequest(BaseModel):
    """Dados do cadastro de empresa + OWNER inicial."""

    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    tax_regime: TaxRegime
    business_profile: BusinessProfile = BusinessProfile.GENERAL
    owner_full_name: str = Field(min_length=2, max_length=255)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)


class OwnerCreatedResponse(BaseModel):
    """Dados públicos do OWNER recém-criado."""

    id: UUID
    email: str
    full_name: str
    role: UserRole


class TenantCreatedResponse(BaseModel):
    """Retorno do cadastro de empresa."""

    id: UUID
    name: str
    slug: str
    tax_regime: TaxRegime
    business_profile: BusinessProfile
    owner: OwnerCreatedResponse


class TenantSettingsResponse(BaseModel):
    """Configurações de sinal, score e tema da clínica."""

    deposit_score_threshold: int | None
    deposit_amount_low_score: Decimal | None
    theme_primary_color: str
    agent_name: str
    agent_tone: str
    agent_welcome_message: str | None
    agent_knowledge: str | None
    agent_cancellation_policy: str | None
    agent_address_info: str | None
    agent_upsell: str | None
    fiscal_enabled: bool
    fiscal_provider: str
    fiscal_municipality: str | None
    fiscal_service_code: str | None
    fiscal_email: str | None
    enable_tithe_and_offering: bool
    tithe_percentage: Decimal
    offering_amount: Decimal
    birthday_credit_amount: Decimal


class TenantSettingsUpdateRequest(BaseModel):
    """Atualização parcial das configurações da clínica."""

    deposit_score_threshold: int | None = Field(default=None, ge=0, le=100)
    deposit_amount_low_score: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    theme_primary_color: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    agent_name: str | None = Field(default=None, min_length=1, max_length=100)
    agent_tone: str | None = Field(default=None, min_length=1, max_length=30)
    agent_welcome_message: str | None = Field(default=None, max_length=3000)
    agent_knowledge: str | None = Field(default=None, max_length=5000)
    agent_cancellation_policy: str | None = Field(default=None, max_length=3000)
    agent_address_info: str | None = Field(default=None, max_length=3000)
    agent_upsell: str | None = Field(default=None, max_length=1000)
    fiscal_enabled: bool | None = None
    fiscal_provider: str | None = Field(default=None, max_length=30)
    fiscal_municipality: str | None = Field(default=None, max_length=120)
    fiscal_service_code: str | None = Field(default=None, max_length=60)
    fiscal_email: str | None = Field(default=None, max_length=255)
    enable_tithe_and_offering: bool | None = None
    tithe_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    offering_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    birthday_credit_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
