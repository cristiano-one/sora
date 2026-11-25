"""Regras de assinaturas de clientes, ciclos e cotas de serviço."""

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.api.schemas.subscriptions import (
    ClientSubscriptionResponse,
    PublicSubscriptionPlanItemResponse,
    PublicSubscriptionPlanResponse,
    PublicSubscriptionResponse,
    SubscriptionQuotaResponse,
)
from app.core.config import settings
from app.models import (
    BillingCycle,
    Client,
    ClientSubscription,
    ClientSubscriptionStatus,
    Service,
    SubscriptionPlan,
    SubscriptionPlanItem,
    SubscriptionUsage,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SubscriptionError(Exception):
    """Dados inválidos para a assinatura."""


class SubscriptionConflictError(Exception):
    """Assinatura já ativa ou em estado incompatível."""


class SubscriptionNotFoundError(Exception):
    """Assinatura/plano inexistente no tenant."""


@dataclass(frozen=True)
class QuotaDecision:
    """Resultado da verificação de cota para um serviço."""

    covered: bool
    available: bool
    reason: str | None = None


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def period_end(plan: SubscriptionPlan, start: datetime) -> datetime:
    """Calcula o fim do ciclo conforme a periodicidade do plano."""
    months = 1 if plan.billing_cycle == BillingCycle.MONTHLY else 3
    return _add_months(start, months)


async def _get_plan(session: AsyncSession, plan_id: UUID) -> SubscriptionPlan:
    plan = await session.get(SubscriptionPlan, plan_id)
    if plan is None or not plan.is_active:
        raise SubscriptionNotFoundError
    return plan


async def create_client_subscription(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    client: Client,
    plan_id: UUID,
    status: ClientSubscriptionStatus = ClientSubscriptionStatus.ACTIVE,
    now: datetime | None = None,
) -> ClientSubscription:
    """Contrata um plano para o cliente e inicia o primeiro ciclo."""
    plan = await _get_plan(session, plan_id)
    start = now or datetime.now(UTC)

    if status == ClientSubscriptionStatus.ACTIVE:
        existing = await session.scalar(
            select(ClientSubscription)
            .where(
                ClientSubscription.client_id == client.id,
                ClientSubscription.plan_id == plan.id,
                ClientSubscription.status == ClientSubscriptionStatus.ACTIVE,
            )
            .limit(1)
        )
        if existing is not None:
            raise SubscriptionConflictError

    subscription = ClientSubscription(
        tenant_id=tenant_id,
        client_id=client.id,
        plan_id=plan.id,
        status=status,
        started_at=start,
        current_period_start=start,
        current_period_end=period_end(plan, start),
        plan=plan,
        client=client,
    )
    session.add(subscription)
    await session.commit()
    return subscription


async def cancel_client_subscription(
    session: AsyncSession,
    subscription: ClientSubscription,
    *,
    now: datetime | None = None,
) -> ClientSubscription:
    """Cancela a assinatura imediatamente (sem reembolso no MVP)."""
    if subscription.status in (
        ClientSubscriptionStatus.CANCELLED,
        ClientSubscriptionStatus.EXPIRED,
    ):
        raise SubscriptionConflictError
    subscription.status = ClientSubscriptionStatus.CANCELLED
    subscription.cancelled_at = now or datetime.now(UTC)
    await session.commit()
    return subscription


async def list_client_subscriptions(
    session: AsyncSession,
    *,
    client_id: UUID | None = None,
    status: ClientSubscriptionStatus | None = None,
) -> list[ClientSubscription]:
    query = select(ClientSubscription).order_by(
        ClientSubscription.created_at.desc()
    )
    if client_id is not None:
        query = query.where(ClientSubscription.client_id == client_id)
    if status is not None:
        query = query.where(ClientSubscription.status == status)
    return list((await session.scalars(query)).all())


async def get_active_subscription(
    session: AsyncSession,
    *,
    client_id: UUID,
    at: datetime | None = None,
) -> ClientSubscription | None:
    moment = at or datetime.now(UTC)
    return await session.scalar(
        select(ClientSubscription)
        .where(
            ClientSubscription.client_id == client_id,
            ClientSubscription.status == ClientSubscriptionStatus.ACTIVE,
            ClientSubscription.current_period_start <= moment,
            ClientSubscription.current_period_end > moment,
        )
        .order_by(ClientSubscription.created_at.desc())
        .limit(1)
    )


def _plan_item(
    subscription: ClientSubscription,
    service_id: UUID,
) -> SubscriptionPlanItem | None:
    for item in subscription.plan.items:
        if item.service_id == service_id:
            return item
    return None


async def quota_decision(
    session: AsyncSession,
    *,
    subscription: ClientSubscription,
    service_id: UUID,
    starts_at: datetime,
) -> QuotaDecision:
    """Verifica cobertura, semana permitida, intervalo e saldo de cota."""
    if (
        subscription.status != ClientSubscriptionStatus.ACTIVE
        or starts_at < subscription.current_period_start
        or starts_at >= subscription.current_period_end
    ):
        return QuotaDecision(covered=False, available=False)

    item = _plan_item(subscription, service_id)
    if item is None:
        return QuotaDecision(covered=False, available=False)

    if item.allowed_weekdays:
        weekday = starts_at.astimezone(
            ZoneInfo(settings.default_tenant_timezone)
        ).weekday()
        if weekday not in item.allowed_weekdays:
            return QuotaDecision(covered=True, available=False, reason="weekday")

    used = await session.scalar(
        select(func.count(SubscriptionUsage.id)).where(
            SubscriptionUsage.subscription_id == subscription.id,
            SubscriptionUsage.service_id == service_id,
            SubscriptionUsage.period_start == subscription.current_period_start,
            SubscriptionUsage.released_at.is_(None),
        )
    )
    if int(used or 0) >= item.uses_per_cycle:
        return QuotaDecision(covered=True, available=False, reason="quota")

    if item.min_interval_days:
        last_used = await session.scalar(
            select(SubscriptionUsage.used_at)
            .where(
                SubscriptionUsage.subscription_id == subscription.id,
                SubscriptionUsage.service_id == service_id,
                SubscriptionUsage.released_at.is_(None),
            )
            .order_by(SubscriptionUsage.used_at.desc())
            .limit(1)
        )
        if last_used is not None and starts_at - last_used < timedelta(
            days=item.min_interval_days
        ):
            return QuotaDecision(
                covered=True,
                available=False,
                reason="interval",
            )

    return QuotaDecision(covered=True, available=True)


async def consume_quota(
    session: AsyncSession,
    *,
    subscription: ClientSubscription,
    service: Service,
    appointment_id: UUID | None,
    used_at: datetime,
) -> SubscriptionUsage:
    """Reserva uma cota no ciclo atual (commit fica com o chamador)."""
    usage = SubscriptionUsage(
        tenant_id=subscription.tenant_id,
        subscription_id=subscription.id,
        client_id=subscription.client_id,
        service_id=service.id,
        appointment_id=appointment_id,
        used_at=used_at,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        service=service,
    )
    session.add(usage)
    return usage


async def release_quota(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    now: datetime | None = None,
) -> bool:
    """Devolve a cota quando o agendamento é cancelado/expirado."""
    usage = await session.scalar(
        select(SubscriptionUsage)
        .where(
            SubscriptionUsage.appointment_id == appointment_id,
            SubscriptionUsage.released_at.is_(None),
        )
        .limit(1)
    )
    if usage is None:
        return False
    usage.released_at = now or datetime.now(UTC)
    return True


async def subscription_quotas(
    session: AsyncSession,
    subscription: ClientSubscription,
) -> list[SubscriptionQuotaResponse]:
    rows = (
        await session.execute(
            select(
                SubscriptionUsage.service_id,
                func.count(SubscriptionUsage.id),
            )
            .where(
                SubscriptionUsage.subscription_id == subscription.id,
                SubscriptionUsage.period_start
                == subscription.current_period_start,
                SubscriptionUsage.released_at.is_(None),
            )
            .group_by(SubscriptionUsage.service_id)
        )
    ).all()
    used_by_service = {service_id: int(count) for service_id, count in rows}

    quotas: list[SubscriptionQuotaResponse] = []
    for item in sorted(
        subscription.plan.items,
        key=lambda value: value.service.name,
    ):
        used = used_by_service.get(item.service_id, 0)
        quotas.append(
            SubscriptionQuotaResponse(
                service_id=item.service_id,
                service_name=item.service.name,
                uses_per_cycle=item.uses_per_cycle,
                used=used,
                remaining=max(item.uses_per_cycle - used, 0),
                min_interval_days=item.min_interval_days,
                allowed_weekdays=item.allowed_weekdays,
            )
        )
    return quotas


async def subscription_response(
    session: AsyncSession,
    subscription: ClientSubscription,
) -> ClientSubscriptionResponse:
    return ClientSubscriptionResponse(
        id=subscription.id,
        client_id=subscription.client_id,
        client_name=subscription.client.full_name,
        plan_id=subscription.plan_id,
        plan_name=subscription.plan.name,
        status=subscription.status,
        started_at=subscription.started_at,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        quotas=await subscription_quotas(session, subscription),
    )


def public_plan_response(
    plan: SubscriptionPlan,
) -> PublicSubscriptionPlanResponse:
    return PublicSubscriptionPlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        billing_cycle=plan.billing_cycle,
        items=[
            PublicSubscriptionPlanItemResponse(
                service_id=item.service_id,
                service_name=item.service.name,
                uses_per_cycle=item.uses_per_cycle,
                min_interval_days=item.min_interval_days,
                allowed_weekdays=item.allowed_weekdays,
            )
            for item in sorted(plan.items, key=lambda value: value.service.name)
        ],
    )


async def public_subscription_response(
    session: AsyncSession,
    subscription: ClientSubscription,
) -> PublicSubscriptionResponse:
    return PublicSubscriptionResponse(
        status=subscription.status,
        plan_id=subscription.plan_id,
        plan_name=subscription.plan.name,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        quotas=await subscription_quotas(session, subscription),
    )
