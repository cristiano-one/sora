"""Regras do catálogo: serviços, pacotes e planos de assinatura."""

from uuid import UUID, uuid4

from app.api.schemas.catalog import (
    PackageCreateRequest,
    ServiceCreateRequest,
    SubscriptionPlanCreateRequest,
)
from app.models import (
    Package,
    PackageItem,
    Service,
    SubscriptionPlan,
    SubscriptionPlanItem,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_SERVICE_UPDATE_FIELDS = frozenset(
    {
        "name",
        "description",
        "duration_minutes",
        "buffer_minutes",
        "price",
        "cost",
        "requires_deposit",
        "deposit_amount",
        "show_average_price",
        "is_active",
    }
)


class CatalogReferenceError(Exception):
    """Serviço referenciado não existe no tenant."""


class CatalogValidationError(Exception):
    """Regra de negócio do catálogo violada."""


async def _ensure_services(session: AsyncSession, service_ids: set[UUID]) -> None:
    if not service_ids:
        return
    found = set(
        (
            await session.scalars(
                select(Service.id).where(Service.id.in_(service_ids))
            )
        ).all()
    )
    if found != service_ids:
        raise CatalogReferenceError


async def create_service(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    body: ServiceCreateRequest,
) -> Service:
    """Cria um serviço no tenant atual (RLS já aplicada)."""
    service = Service(
        tenant_id=tenant_id,
        name=body.name.strip(),
        description=body.description,
        duration_minutes=body.duration_minutes,
        buffer_minutes=body.buffer_minutes,
        price=body.price,
        cost=body.cost,
        requires_deposit=body.requires_deposit,
        deposit_amount=body.deposit_amount,
        show_average_price=body.show_average_price,
        is_active=body.is_active,
    )
    session.add(service)
    await session.commit()
    return service


async def update_service(
    session: AsyncSession,
    *,
    service: Service,
    changes: dict[str, object],
) -> Service:
    """Aplica alterações parciais e valida a coerência do sinal."""
    for field in _SERVICE_UPDATE_FIELDS:
        if field in changes:
            setattr(service, field, changes[field])

    if service.requires_deposit and (
        service.deposit_amount is None or service.deposit_amount <= 0
    ):
        raise CatalogValidationError(
            "deposit_amount é obrigatório e positivo quando requires_deposit=true"
        )

    await session.commit()
    return service


async def create_package(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    body: PackageCreateRequest,
) -> Package:
    """Cria um pacote e seus itens na mesma transação."""
    await _ensure_services(session, {item.service_id for item in body.items})

    package = Package(
        id=uuid4(),
        tenant_id=tenant_id,
        name=body.name.strip(),
        description=body.description,
        total_price=body.total_price,
        is_active=body.is_active,
        items=[
            PackageItem(
                tenant_id=tenant_id,
                service_id=item.service_id,
                quantity=item.quantity,
            )
            for item in body.items
        ],
    )
    session.add(package)
    await session.commit()
    return package


async def update_package(
    session: AsyncSession,
    *,
    package: Package,
    changes: dict[str, object],
) -> Package:
    """Atualiza dados do pacote (itens não são alterados neste passo)."""
    for field in ("name", "description", "total_price", "is_active"):
        if field in changes:
            setattr(package, field, changes[field])
    await session.commit()
    return package


async def create_subscription_plan(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    body: SubscriptionPlanCreateRequest,
) -> SubscriptionPlan:
    """Cria um plano recorrente e suas cotas na mesma transação."""
    await _ensure_services(session, {item.service_id for item in body.items})

    plan = SubscriptionPlan(
        id=uuid4(),
        tenant_id=tenant_id,
        name=body.name.strip(),
        description=body.description,
        price=body.price,
        billing_cycle=body.billing_cycle,
        is_active=body.is_active,
        items=[
            SubscriptionPlanItem(
                tenant_id=tenant_id,
                service_id=item.service_id,
                uses_per_cycle=item.uses_per_cycle,
                min_interval_days=item.min_interval_days,
                allowed_weekdays=item.allowed_weekdays,
            )
            for item in body.items
        ],
    )
    session.add(plan)
    await session.commit()
    return plan


async def update_subscription_plan(
    session: AsyncSession,
    *,
    plan: SubscriptionPlan,
    changes: dict[str, object],
) -> SubscriptionPlan:
    """Atualiza dados do plano (cotas não são alteradas neste passo)."""
    for field in ("name", "description", "price", "billing_cycle", "is_active"):
        if field in changes:
            setattr(plan, field, changes[field])
    await session.commit()
    return plan
