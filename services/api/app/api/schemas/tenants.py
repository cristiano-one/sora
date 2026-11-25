"""Contratos do módulo de tenants."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import TaxRegime, UserRole


class CurrentTenantResponse(BaseModel):
    """Dados públicos do tenant atual."""

    id: UUID
    name: str
    slug: str
    tax_regime: TaxRegime


class TenantCreateRequest(BaseModel):
    """Dados do cadastro de empresa + OWNER inicial."""

    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    tax_regime: TaxRegime
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
    owner: OwnerCreatedResponse
