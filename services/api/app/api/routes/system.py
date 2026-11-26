"""Console master do provedor: perfis de negócio por tenant."""

import hmac
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.system import (
    SystemLoginRequest,
    SystemLoginResponse,
    SystemProfileUpdateRequest,
    SystemTenantResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.config import settings
from app.core.redis import get_redis
from app.db.rls import set_tenant_context
from app.db.session import get_system_session
from app.models import Tenant

router = APIRouter(prefix="/system", tags=["system"])

SESSION_TTL_SECONDS = 30 * 60
MAX_ATTEMPTS = 10
ATTEMPT_WINDOW_SECONDS = 15 * 60


def _session_key(token: str) -> str:
    return f"system:admin:session:{token}"


def _attempts_key(ip: str) -> str:
    return f"system:admin:attempts:{ip}"


async def require_system_admin(
    token: str = Header(default="", alias="X-System-Token"),
    redis: Redis = Depends(get_redis),
) -> str:
    """Valida a sessão master emitida pelo console do provedor."""
    if not token or await redis.get(_session_key(token)) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão do sistema inválida ou expirada",
        )
    return token


def _tenant_response(tenant: Tenant) -> SystemTenantResponse:
    return SystemTenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        tax_regime=tenant.tax_regime,
        business_profile=tenant.business_profile,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


@router.post(
    "/login",
    response_model=SystemLoginResponse,
    summary="Autentica o administrador do sistema com a senha master",
)
async def system_login(
    body: SystemLoginRequest,
    request: Request,
    redis: Redis = Depends(get_redis),
) -> SystemLoginResponse:
    if not settings.system_admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Senha master do sistema não configurada",
        )
    ip = client_ip(request) or "unknown"
    attempts_key = _attempts_key(ip)
    attempts = int(await redis.get(attempts_key) or 0)
    if attempts >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente mais tarde.",
        )
    if not hmac.compare_digest(
        body.password,
        settings.system_admin_password,
    ):
        await redis.incr(attempts_key)
        await redis.expire(attempts_key, ATTEMPT_WINDOW_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha master inválida",
        )
    await redis.delete(attempts_key)
    token = secrets.token_urlsafe(40)
    await redis.set(_session_key(token), "1", ex=SESSION_TTL_SECONDS)
    return SystemLoginResponse(token=token, expires_in=SESSION_TTL_SECONDS)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerra a sessão master",
)
async def system_logout(
    token: str = Depends(require_system_admin),
    redis: Redis = Depends(get_redis),
) -> None:
    await redis.delete(_session_key(token))


@router.get(
    "/tenants",
    response_model=list[SystemTenantResponse],
    summary="Lista todas as empresas da plataforma",
)
async def list_system_tenants(
    _token: str = Depends(require_system_admin),
    session: AsyncSession = Depends(get_system_session),
) -> list[SystemTenantResponse]:
    tenants = (
        await session.scalars(select(Tenant).order_by(Tenant.name))
    ).all()
    return [_tenant_response(tenant) for tenant in tenants]


@router.patch(
    "/tenants/{tenant_id}/profile",
    response_model=SystemTenantResponse,
    summary="Define o perfil de negócio de uma empresa",
)
async def update_tenant_profile(
    tenant_id: UUID,
    body: SystemProfileUpdateRequest,
    request: Request,
    _token: str = Depends(require_system_admin),
    session: AsyncSession = Depends(get_system_session),
) -> SystemTenantResponse:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )
    previous = tenant.business_profile.value
    tenant.business_profile = body.business_profile
    await session.commit()
    await set_tenant_context(session, tenant.id)
    await record_audit(
        session,
        tenant_id=tenant.id,
        actor=None,
        action="system.tenant.profile",
        resource_type="tenant",
        resource_id=tenant.id,
        ip_address=client_ip(request),
        details={
            "from": previous,
            "to": body.business_profile.value,
            "source": "system_admin",
        },
    )
    return _tenant_response(tenant)
