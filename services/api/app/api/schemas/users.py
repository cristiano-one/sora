"""Contratos de usuários/colaboradores e comissões."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import CommissionBase, UserRole


class UserCreateRequest(BaseModel):
    """Cadastro de colaborador/admin (OWNER é criado no signup do tenant)."""

    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    commission_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    commission_fixed: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    commission_base: CommissionBase = CommissionBase.GROSS


class UserUpdateRequest(BaseModel):
    """Atualização parcial de colaborador/admin."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None
    role: UserRole | None = None
    commission_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    commission_fixed: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    commission_base: CommissionBase | None = None


class UserResponse(BaseModel):
    """Dados públicos de um usuário (sem hash de senha)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    commission_percentage: Decimal | None
    commission_fixed: Decimal | None
    commission_base: CommissionBase


class CommissionResponse(BaseModel):
    """Comissão do próprio usuário autenticado."""

    user_id: UUID
    commission_percentage: Decimal | None
    commission_fixed: Decimal | None
    commission_base: CommissionBase
