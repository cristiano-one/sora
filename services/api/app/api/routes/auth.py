"""Endpoints de autenticação (login, refresh, logout e perfil)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import Principal, get_current_principal
from app.core.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    TokenPair,
)
from app.core.auth.service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    revoke_access_token,
    revoke_refresh_token,
)
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
