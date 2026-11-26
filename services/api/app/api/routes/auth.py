"""Endpoints de autenticação (login, refresh, logout, perfil e senha)."""

import secrets
from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import Principal, get_current_principal
from app.core.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.core.auth.security import (
    hash_password,
    invite_key,
    password_reset_key,
)
from app.core.auth.service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    revoke_access_token,
    revoke_all_sessions,
    revoke_refresh_token,
)
from app.core.config import settings
from app.core.email import send_email
from app.core.redis import get_redis
from app.db.rls import set_tenant_context
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Autentica e emite o par de tokens",
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> TokenPair:
    try:
        return await AuthService(session, redis).login(
            tenant_slug=body.tenant_slug,
            email=str(body.email),
            password=body.password,
        )
    except InvalidCredentialsError as exc:
        raise _invalid_credentials() from exc


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotaciona o refresh token e emite um novo par",
)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> TokenPair:
    try:
        return await AuthService(session, redis).refresh(body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise _invalid_credentials() from exc


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga a sessão atual",
)
async def logout(
    principal: Principal = Depends(get_current_principal),
    body: LogoutRequest | None = None,
    redis: Redis = Depends(get_redis),
) -> Response:
    await revoke_access_token(
        redis,
        tenant_id=principal.tenant_id,
        jti=principal.jti,
        expires_at=principal.expires_at,
    )
    if body is not None and body.refresh_token:
        await revoke_refresh_token(
            redis,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            refresh_token=body.refresh_token,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Retorna o usuário autenticado",
)
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    await set_tenant_context(session, principal.tenant_id)
    user = await session.get(User, principal.user_id)
    if user is None:
        raise _invalid_credentials()
    return MeResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


async def _find_tenant(session: AsyncSession, slug: str) -> UUID | None:
    value = await session.scalar(
        text("SELECT public.resolve_tenant_id_by_slug(:slug)"),
        {"slug": slug.strip().lower()},
    )
    if value is None:
        return None
    return UUID(str(value))


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia link de recuperação de senha",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    tenant_id = await _find_tenant(session, body.tenant_slug)
    if tenant_id is not None:
        await set_tenant_context(session, tenant_id)
        user = await session.scalar(
            select(User).where(
                User.email == str(body.email).strip().lower(),
                User.is_active.is_(True),
            )
        )
        if user is not None:
            token = secrets.token_urlsafe(32)
            await redis.set(
                password_reset_key(tenant_id, token),
                str(user.id),
                ex=30 * 60,
            )
            link = (
                f"{settings.web_base_url}/redefinir-senha"
                f"?tenant={body.tenant_slug.strip().lower()}&token={token}"
            )
            send_email(
                to=user.email,
                subject="Recuperação de senha — Sora Studio",
                body=(
                    f"Olá, {user.full_name}.\n\n"
                    f"Para definir uma nova senha, acesse:\n{link}\n\n"
                    "O link expira em 30 minutos."
                ),
            )
    return {
        "message": (
            "Se o e-mail existir, enviaremos um link de recuperação."
        )
    }


async def _reset_password(
    session: AsyncSession,
    redis: Redis,
    *,
    body: ResetPasswordRequest,
    key_factory: Callable[[UUID, str], str],
) -> None:
    tenant_id = await _find_tenant(session, body.tenant_slug)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )
    key = key_factory(tenant_id, body.token)
    user_id = await redis.get(key)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )
    await set_tenant_context(session, tenant_id)
    user = await session.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )
    user.hashed_password = hash_password(body.new_password)
    await session.commit()
    await redis.delete(key)
    await revoke_all_sessions(
        redis,
        tenant_id=tenant_id,
        user_id=user.id,
    )


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Define nova senha com token de recuperação",
)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    await _reset_password(
        session,
        redis,
        body=body,
        key_factory=password_reset_key,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/accept-invite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Aceita convite e define a senha inicial",
)
async def accept_invite(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    await _reset_password(
        session,
        redis,
        body=body,
        key_factory=invite_key,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
