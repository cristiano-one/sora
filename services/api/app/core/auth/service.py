"""Regras de autenticação: login, refresh rotativo e revogação."""

import time
import uuid
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.schemas import TokenPair
from app.core.auth.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    denylist_key,
    refresh_key,
    revoked_at_key,
    verify_dummy_password,
    verify_password,
)
from app.core.config import settings
from app.db.rls import set_tenant_context
from app.models.user import User


class InvalidCredentialsError(Exception):
    """Credenciais inválidas (mensagem pública sempre genérica)."""


class InvalidRefreshTokenError(Exception):
    """Refresh token inválido, expirado, revogado ou reutilizado."""


async def revoke_access_token(
    redis: Redis,
    *,
    tenant_id: UUID,
    jti: str,
    expires_at: datetime,
) -> None:
    """Adiciona o access token à denylist até seu vencimento."""
    ttl = int(expires_at.timestamp()) - int(time.time())
    if ttl > 0:
        await redis.set(denylist_key(tenant_id, jti), "1", ex=ttl)


async def revoke_refresh_token(
    redis: Redis,
    *,
    tenant_id: UUID,
    user_id: UUID,
    refresh_token: str,
) -> None:
    """Remove o refresh token do Redis (idempotente e sem vazar erros)."""
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except InvalidTokenError:
        return
    if payload.tenant_id == tenant_id and payload.user_id == user_id:
        await redis.delete(refresh_key(payload.tenant_id, payload.jti))


async def revoke_all_sessions(
    redis: Redis,
    *,
    tenant_id: UUID,
    user_id: UUID,
) -> None:
    """Invalida todos os tokens do usuário a partir de agora."""
    ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    await redis.set(
        revoked_at_key(tenant_id, user_id),
        str(int(time.time() * 1000)),
        ex=ttl,
    )


class AuthService:
    """Orquestra login e rotação de tokens com contexto RLS."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis

    async def login(self, *, tenant_slug: str, email: str, password: str) -> TokenPair:
        tenant_id = await self._resolve_tenant(tenant_slug)
        if tenant_id is None:
            verify_dummy_password(password)
            raise InvalidCredentialsError

        await set_tenant_context(self.session, tenant_id)
        user = await self.session.scalar(
            select(User).where(User.email == email.strip().lower())
        )
        if user is None or not user.is_active:
            verify_dummy_password(password)
            raise InvalidCredentialsError
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError

        return await self._issue_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except InvalidTokenError as exc:
            raise InvalidRefreshTokenError from exc

        revoked_at = await self.redis.get(
            revoked_at_key(payload.tenant_id, payload.user_id)
        )
        if revoked_at is not None and payload.issued_at_ms < int(revoked_at):
            raise InvalidRefreshTokenError

        stored_user_id = await self.redis.getdel(
            refresh_key(payload.tenant_id, payload.jti)
        )
        if stored_user_id is None or stored_user_id != str(payload.user_id):
            # Reuso de token (ou token já rotacionado): revoga todas as sessões.
            await revoke_all_sessions(
                self.redis,
                tenant_id=payload.tenant_id,
                user_id=payload.user_id,
            )
            raise InvalidRefreshTokenError

        await set_tenant_context(self.session, payload.tenant_id)
        user = await self.session.get(User, payload.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        return await self._issue_pair(user)

    async def _resolve_tenant(self, slug: str) -> UUID | None:
        value = await self.session.scalar(
            text("SELECT public.resolve_tenant_id_by_slug(:slug)"),
            {"slug": slug.strip().lower()},
        )
        if value is None:
            return None
        return uuid.UUID(str(value))

    async def _issue_pair(self, user: User) -> TokenPair:
        access_token, _, _ = create_access_token(user.id, user.tenant_id, user.role)
        refresh_token, refresh_jti, _ = create_refresh_token(
            user.id,
            user.tenant_id,
            user.role,
        )
        ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        await self.redis.set(
            refresh_key(user.tenant_id, refresh_jti),
            str(user.id),
            ex=ttl,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
