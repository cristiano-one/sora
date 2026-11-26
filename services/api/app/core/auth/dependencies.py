"""Dependência de autenticação: deriva o Principal do access token."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.security import (
    InvalidTokenError,
    TokenType,
    decode_token,
    denylist_key,
    revoked_at_key,
)
from app.core.redis import get_redis
from app.db.rls import set_tenant_context
from app.db.session import get_session
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """Contexto autenticado injetado nas rotas."""

    user_id: UUID
    tenant_id: UUID
    role: UserRole
    jti: str
    issued_at: datetime
    expires_at: datetime


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    redis: Redis = Depends(get_redis),
) -> Principal:
    """Valida o access token, denylist e revogação em massa do usuário."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    if await redis.exists(denylist_key(payload.tenant_id, payload.jti)):
        raise _unauthorized()

    revoked_at = await redis.get(revoked_at_key(payload.tenant_id, payload.user_id))
    if revoked_at is not None and payload.issued_at_ms < int(revoked_at):
        raise _unauthorized()

    return Principal(
        user_id=payload.user_id,
        tenant_id=payload.tenant_id,
        role=payload.role,
        jti=payload.jti,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
    )


def require_roles(*allowed_roles: UserRole) -> Callable[..., Awaitable[Principal]]:
    """Fábrica de dependência que exige um dos papéis informados (RBAC)."""

    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )
        return principal

    return dependency


async def get_tenant_session(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[AsyncSession]:
    """Fornece a sessão com app.current_tenant_id já definido (RLS)."""
    await set_tenant_context(session, principal.tenant_id)
    yield session


async def require_ai_inbox(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    """Permite OWNER/ADMIN ou colaborador com permissão explícita.

    A permissão é lida do banco em cada requisição para que a revogação tenha
    efeito imediato, sem esperar o token expirar.
    """
    if principal.role in (UserRole.OWNER, UserRole.ADMIN):
        return principal
    await set_tenant_context(session, principal.tenant_id)
    user = await session.get(User, principal.user_id)
    if (
        user is None
        or not user.is_active
        or not user.can_manage_ai_inbox
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )
    return principal
