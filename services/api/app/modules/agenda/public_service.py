"""Link mágico e agendamento público (sem login)."""

import re
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.api.schemas.agenda import AvailabilityResponse
from app.api.schemas.public_booking import (
    MagicLinkResponse,
    PublicAppointmentResponse,
    PublicContextResponse,
    PublicProfessionalResponse,
    PublicServiceResponse,
)
from app.api.schemas.subscriptions import PublicSubscriptionResponse
from app.core.config import settings
from app.core.redis import tenant_key
from app.db.rls import set_tenant_context
from app.models import (
    Client,
    ClientSubscriptionStatus,
    Service,
    SubscriptionPlan,
    Tenant,
    User,
    UserRole,
)
from app.modules.agenda.service import (
    _as_utc,
    _compute_slots,
    _insert_appointment,
    resolve_quota_subscription,
)
from app.modules.subscriptions.service import (
    SubscriptionConflictError,
    SubscriptionNotFoundError,
    create_client_subscription,
    get_active_subscription,
    public_plan_response,
    public_subscription_response,
)
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

MAGIC_TOKEN_TTL_SECONDS = 20 * 60


class InvalidMagicLinkError(Exception):
    """Token ausente, inválido ou expirado."""


class PublicTenantNotFoundError(Exception):
    """Slug de clínica inexistente/inativo."""


class PublicBookingError(Exception):
    """Dados inválidos no fluxo público."""


class PublicBookingConflictError(Exception):
    """Conflito genérico (inclui cliente bloqueado, sem revelar o motivo)."""


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        raise PublicBookingError("Telefone inválido")
    return digits


async def _tenant_id_by_slug(session: AsyncSession, slug: str) -> UUID | None:
    value = await session.scalar(
        text("SELECT public.resolve_tenant_id_by_slug(:slug)"),
        {"slug": slug.strip().lower()},
    )
    if value is None:
        return None
    return UUID(str(value))


async def _client_by_phone(session: AsyncSession, phone: str) -> Client | None:
    digits = normalize_phone(phone)
    return await session.scalar(
        select(Client)
        .where(func.regexp_replace(Client.phone, "[^0-9]", "", "g") == digits)
        .limit(1)
    )


async def create_magic_link(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    phone: str,
) -> MagicLinkResponse:
    """Gera token no Redis (TTL 20 min) e devolve o link leve."""
    tenant_id = await _tenant_id_by_slug(session, slug)
    if tenant_id is None:
        raise PublicTenantNotFoundError

    digits = normalize_phone(phone)
    token = uuid4().hex
    await redis.set(
        tenant_key(tenant_id, "public", "magic", token),
        digits,
        ex=MAGIC_TOKEN_TTL_SECONDS,
    )
    base = settings.public_booking_base_url.rstrip("/")
    return MagicLinkResponse(
        url=f"{base}/public/{slug}?t={token}",
        expires_in=MAGIC_TOKEN_TTL_SECONDS,
    )


async def _validate_magic(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
) -> tuple[UUID, str]:
    tenant_id = await _tenant_id_by_slug(session, slug)
    if tenant_id is None:
        raise PublicTenantNotFoundError

    phone = await redis.get(tenant_key(tenant_id, "public", "magic", token))
    if phone is None:
        raise InvalidMagicLinkError

    await set_tenant_context(session, tenant_id)
    return tenant_id, str(phone)


async def get_public_context(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
) -> PublicContextResponse:
    """Retorna apenas dados públicos da clínica e o nome do próprio cliente."""
    tenant_id, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise PublicTenantNotFoundError

    services = (
        await session.scalars(
            select(Service).where(Service.is_active).order_by(Service.name)
        )
    ).all()
    professionals = (
        await session.scalars(
            select(User)
            .where(User.is_active, User.role == UserRole.COLLABORATOR)
            .order_by(User.full_name)
        )
    ).all()
    client = await _client_by_phone(session, phone)
    plans = (
        await session.scalars(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active)
            .order_by(SubscriptionPlan.name)
        )
    ).all()
    active_subscription = (
        await get_active_subscription(session, client_id=client.id)
        if client is not None
        else None
    )

    return PublicContextResponse(
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        client_name=client.full_name if client is not None else None,
        services=[
            PublicServiceResponse(
                id=service.id,
                name=service.name,
                duration_minutes=service.duration_minutes,
                price=service.price if service.show_average_price else None,
            )
            for service in services
        ],
        professionals=[
            PublicProfessionalResponse(id=user.id, full_name=user.full_name)
            for user in professionals
        ],
        plans=[public_plan_response(plan) for plan in plans],
        subscription=(
            await public_subscription_response(session, active_subscription)
            if active_subscription is not None
            else None
        ),
    )


async def _public_service(
    session: AsyncSession,
    service_id: UUID,
) -> Service:
    service = await session.get(Service, service_id)
    if service is None or not service.is_active:
        raise PublicBookingError("Serviço inválido")
    return service


async def _public_professional(
    session: AsyncSession,
    collaborator_id: UUID,
) -> User:
    professional = await session.get(User, collaborator_id)
    if (
        professional is None
        or not professional.is_active
        or professional.role != UserRole.COLLABORATOR
    ):
        raise PublicBookingError("Profissional inválido")
    return professional


async def public_availability(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
    service_id: UUID,
    collaborator_id: UUID,
    day: date,
) -> AvailabilityResponse:
    """Disponibilidade pública; cliente bloqueado recebe lista vazia (neutro)."""
    _, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    service = await _public_service(session, service_id)
    professional = await _public_professional(session, collaborator_id)
    client = await _client_by_phone(session, phone)

    if client is not None and client.is_blocked:
        return AvailabilityResponse(
            collaborator_id=professional.id,
            service_id=service.id,
            date=day,
            duration_minutes=service.duration_minutes,
            buffer_minutes=service.buffer_minutes,
            available=False,
            available_slots=[],
        )

    return await _compute_slots(
        session,
        collaborator=professional,
        service=service,
        day=day,
    )


async def public_create_appointment(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
    service_id: UUID,
    collaborator_id: UUID,
    starts_at: datetime,
    full_name: str,
) -> PublicAppointmentResponse:
    """Cria o agendamento público usando as mesmas travas do fluxo interno."""
    tenant_id, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    service = await _public_service(session, service_id)
    professional = await _public_professional(session, collaborator_id)

    start = _as_utc(starts_at)
    if start <= datetime.now(UTC):
        raise PublicBookingError("Horário inválido")

    client = await _client_by_phone(session, phone)
    if client is not None and client.is_blocked:
        raise PublicBookingConflictError(
            "Não foi possível concluir o agendamento. Fale com a recepção."
        )

    if client is None:
        name = full_name.strip()
        if len(name) < 2:
            raise PublicBookingError("Informe seu nome")
        client = Client(
            tenant_id=tenant_id,
            full_name=name,
            phone=phone,
            score=100,
            is_blocked=False,
        )
        session.add(client)
        await session.flush()

    appointment = await _insert_appointment(
        session,
        redis,
        tenant_id=tenant_id,
        collaborator=professional,
        client=client,
        service=service,
        start=start,
        notes=None,
        created_by=None,
        subscription=await resolve_quota_subscription(
            session,
            client=client,
            service=service,
            start=start,
        ),
    )
    return PublicAppointmentResponse(
        id=appointment.id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        status=appointment.status,
        service_name=service.name,
        collaborator_name=professional.full_name,
        deposit_amount=appointment.deposit_amount,
        used_subscription=appointment.subscription_id is not None,
    )


async def public_create_subscription(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
    plan_id: UUID,
    full_name: str | None,
) -> PublicSubscriptionResponse:
    """Contrata um plano pelo link mágico (cliente existente ou novo)."""
    tenant_id, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    client = await _client_by_phone(session, phone)
    if client is not None and client.is_blocked:
        raise PublicBookingConflictError(
            "Não foi possível concluir a contratação. Fale com a recepção."
        )

    if client is None:
        name = (full_name or "").strip()
        if len(name) < 2:
            raise PublicBookingError("Informe seu nome")
        client = Client(
            tenant_id=tenant_id,
            full_name=name,
            phone=phone,
            score=100,
            is_blocked=False,
        )
        session.add(client)
        await session.flush()

    try:
        subscription = await create_client_subscription(
            session,
            tenant_id=tenant_id,
            client=client,
            plan_id=plan_id,
            status=ClientSubscriptionStatus.ACTIVE,
        )
    except SubscriptionConflictError as exc:
        raise PublicBookingConflictError(
            "Você já possui uma assinatura ativa."
        ) from exc
    except SubscriptionNotFoundError as exc:
        raise PublicBookingError("Plano inválido") from exc

    return await public_subscription_response(session, subscription)
