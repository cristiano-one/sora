"""Endpoints de tenants: cadastro de empresa e leitura do tenant atual."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tenants import (
    CurrentTenantResponse,
    OwnerCreatedResponse,
    TenantCreatedResponse,
    TenantCreateRequest,
    TenantSettingsResponse,
    TenantSettingsUpdateRequest,
)
from app.core.auth.dependencies import Principal, get_tenant_session, require_roles
from app.db.session import get_session
from app.models import Tenant, UserRole
from app.modules.tenants.service import (
    SlugAlreadyExistsError,
    create_tenant_with_owner,
)
from app.modules.tenants.settings import (
    TenantSettingsValidationError,
    get_tenant_settings_response,
    update_tenant_settings,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])

_require_owner_or_admin = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.post(
    "",
    response_model=TenantCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra empresa e OWNER inicial",
)
async def create_tenant(
    body: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TenantCreatedResponse:
    try:
        tenant, owner = await create_tenant_with_owner(
            session,
            name=body.name,
            slug=body.slug,
            tax_regime=body.tax_regime,
            owner_full_name=body.owner_full_name,
            owner_email=str(body.owner_email),
            owner_password=body.owner_password,
        )
    except SlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug indisponível",
        ) from exc

    return TenantCreatedResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        tax_regime=tenant.tax_regime,
        owner=OwnerCreatedResponse(
            id=owner.id,
            email=owner.email,
            full_name=owner.full_name,
            role=owner.role,
        ),
    )


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
    return CurrentTenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        tax_regime=tenant.tax_regime,
    )


@router.get(
    "/settings",
    response_model=TenantSettingsResponse,
    summary="Retorna configurações de sinal, score e tema",
)
async def current_tenant_settings(
    principal: Principal = Depends(_require_owner_or_admin),
    session: AsyncSession = Depends(get_tenant_session),
) -> TenantSettingsResponse:
    return await get_tenant_settings_response(session, principal.tenant_id)


@router.patch(
    "/settings",
    response_model=TenantSettingsResponse,
    summary="Atualiza configurações de sinal, score e tema",
)
async def update_tenant_settings_endpoint(
    body: TenantSettingsUpdateRequest,
    principal: Principal = Depends(_require_owner_or_admin),
    session: AsyncSession = Depends(get_tenant_session),
) -> TenantSettingsResponse:
    try:
        return await update_tenant_settings(
            session,
            tenant_id=principal.tenant_id,
            changes=body.model_dump(exclude_unset=True),
        )
    except TenantSettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
