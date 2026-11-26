"""Contratos Pydantic da autenticação."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.tenant import BusinessProfile
from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Credenciais de login (tenant resolvido pelo slug/subdomínio)."""

    tenant_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Refresh token a ser rotacionado."""

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """Refresh token opcional a ser revogado junto com o access token."""

    refresh_token: str | None = None


class TokenPair(BaseModel):
    """Par de tokens emitido no login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    """Dados do próprio usuário autenticado (sem campos internos)."""

    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: UserRole
    business_profile: BusinessProfile


class ForgotPasswordRequest(BaseModel):
    """Pedido de recuperação de senha."""

    tenant_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Definição de nova senha via token de recuperação/convite."""

    tenant_slug: str = Field(min_length=1, max_length=100)
    token: str = Field(min_length=10, max_length=500)
    new_password: str = Field(min_length=8, max_length=128)
