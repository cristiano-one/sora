"""Contratos do console master do provedor."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import BusinessProfile, TaxRegime


class SystemLoginRequest(BaseModel):
    """Senha master do administrador do sistema."""

    password: str = Field(min_length=1, max_length=200)


class SystemLoginResponse(BaseModel):
    """Sessão temporária do console master."""

    token: str
    expires_in: int


class SystemTenantResponse(BaseModel):
    """Tenant visível para o administrador do sistema."""

    id: UUID
    name: str
    slug: str
    tax_regime: TaxRegime
    business_profile: BusinessProfile
    is_active: bool
    created_at: datetime


class SystemProfileUpdateRequest(BaseModel):
    """Novo perfil de negócio do tenant."""

    business_profile: BusinessProfile
