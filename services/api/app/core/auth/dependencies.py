"""Dependência de autenticação: deriva o Principal do access token."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from app.core.auth.security import (
    InvalidTokenError,
    TokenType,
    decode_token,
    denylist_key,
    revoked_at_key,
)
from app.core.redis import get_redis
from app.models.user import UserRole

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
