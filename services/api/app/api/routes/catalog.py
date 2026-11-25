"""Endpoints do catálogo: serviços, pacotes e planos de assinatura."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.catalog import (
    PackageCreateRequest,
    PackageResponse,
    PackageUpdateRequest,
    ServiceCreateRequest,
    ServiceResponse,
    ServiceUpdateRequest,
    SubscriptionPlanCreateRequest,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdateRequest,
)
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.models import Package, Service, SubscriptionPlan, UserRole
from app.modules.catalog.service import (
    CatalogReferenceError,
    CatalogValidationError,
    create_package,
    create_service,
    create_subscription_plan,
    update_package,
    update_service,
    update_subscription_plan,
)

router = APIRouter(tags=["catalog"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.get(
    "/services",
    response_model=list[ServiceResponse],
    summary="Lista serviços do tenant",
)
async def list_services(
    session: AsyncSession = Depends(get_tenant_session),
) -> list[Service]:
    result = await session.scalars(select(Service).order_by(Service.name))
    return list(result.all())


@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra serviço",
)
async def create_service_endpoint(
    body: ServiceCreateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> Service:
    return await create_service(
        session,
        tenant_id=principal.tenant_id,
        body=body,
    )


@router.patch(
    "/services/{service_id}",
    response_model=ServiceResponse,
    summary="Atualiza serviço",
)
async def update_service_endpoint(
    service_id: UUID,
    body: ServiceUpdateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serviço não encontrado",
        )
    try:
        return await update_service(
            session,
            service=service,
            changes=body.model_dump(exclude_unset=True),
        )
    except CatalogValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/packages",
    response_model=list[PackageResponse],
    summary="Lista pacotes do tenant",
)
async def list_packages(
    session: AsyncSession = Depends(get_tenant_session),
) -> list[Package]:
    result = await session.scalars(select(Package).order_by(Package.name))
    return list(result.all())


@router.post(
    "/packages",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra pacote de serviços",
)
async def create_package_endpoint(
    body: PackageCreateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> Package:
    try:
        return await create_package(
            session,
            tenant_id=principal.tenant_id,
            body=body,
        )
    except CatalogReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serviço não encontrado",
        ) from exc


@router.patch(
    "/packages/{package_id}",
    response_model=PackageResponse,
    summary="Atualiza pacote",
)
async def update_package_endpoint(
    package_id: UUID,
    body: PackageUpdateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> Package:
    package = await session.scalar(
        select(Package).where(Package.id == package_id)
    )
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pacote não encontrado",
        )
    return await update_package(
        session,
        package=package,
        changes=body.model_dump(exclude_unset=True),
    )


@router.get(
    "/subscription-plans",
    response_model=list[SubscriptionPlanResponse],
    summary="Lista planos de assinatura do tenant",
)
async def list_subscription_plans(
    session: AsyncSession = Depends(get_tenant_session),
) -> list[SubscriptionPlan]:
    result = await session.scalars(
        select(SubscriptionPlan).order_by(SubscriptionPlan.name)
    )
    return list(result.all())


@router.post(
    "/subscription-plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra plano de assinatura",
)
async def create_subscription_plan_endpoint(
    body: SubscriptionPlanCreateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SubscriptionPlan:
    try:
        return await create_subscription_plan(
            session,
            tenant_id=principal.tenant_id,
            body=body,
        )
    except CatalogReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serviço não encontrado",
        ) from exc


@router.patch(
    "/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    summary="Atualiza plano de assinatura",
)
async def update_subscription_plan_endpoint(
    plan_id: UUID,
    body: SubscriptionPlanUpdateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> SubscriptionPlan:
    plan = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado",
        )
    return await update_subscription_plan(
        session,
        plan=plan,
        changes=body.model_dump(exclude_unset=True),
    )
