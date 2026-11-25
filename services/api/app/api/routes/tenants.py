"""Endpoints do tenant atual (RBAC + RLS)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tenants import CurrentTenantResponse
from app.core.auth.dependencies import Principal, get_tenant_session, require_roles
from app.models import Tenant, UserRole

router = APIRouter(prefix="/tenants", tags=["tenants"])

_require_owner_or_admin = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.get(
    "/current",
    response_model=CurrentTenantResponse,
    summary="Retorna o tenant do usuário autenticado",
)
async def current_tenant(
    principal: Principal = Depends(_require_owner_or_admin),
    session: AsyncSession = Depends(get_tenant_session),
) -> CurrentTenantResponse:
    tenant = await session.get(Tenant, principal.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado",
        )
    return CurrentTenantResponse(id=tenant.id, name=tenant.name, slug=tenant.slug)
