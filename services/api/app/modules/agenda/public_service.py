"""Link mágico e agendamento público (sem login)."""

import re
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from app.api.schemas.agenda import AvailabilityResponse
from app.api.schemas.payments import PublicPaymentConfirmResponse
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
    Appointment,
    AppointmentStatus,
    Client,
    ClientSubscription,
    ClientSubscriptionStatus,
    PaymentStatus,
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
    expire_pending_deposits,
    resolve_deposit_amount,
    resolve_quota_subscription,
)
from app.modules.payments.service import (
    confirm_payment,
    create_payment_intent,
    expire_payment,
    get_payment,
    get_payment_for_appointment,
    get_payment_for_subscription,
    payment_response,
)
from app.modules.subscriptions.service import (
    SubscriptionConflictError,
    SubscriptionNotFoundError,
    create_client_subscription,
    get_active_subscription,
    get_latest_subscription,
    public_plan_response,
    public_subscription_response,
)
from app.modules.tenants.settings import (
    DEFAULT_THEME_COLOR,
    get_tenant_settings,
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


class PaymentNotFoundError(Exception):
    """Pagamento inexistente ou de outro cliente."""


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
    tenant_settings = await get_tenant_settings(session, tenant_id)

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
        theme_primary_color=(
            tenant_settings.theme_primary_color
            if tenant_settings is not None
            else DEFAULT_THEME_COLOR
        ),
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
    await expire_pending_deposits(session, tenant_id=tenant_id)
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

    subscription = await resolve_quota_subscription(
        session,
        client=client,
        service=service,
        start=start,
    )
    deposit_amount = (
        None
        if subscription is not None
        else await resolve_deposit_amount(
            session,
            tenant_id=tenant_id,
            client=client,
            service=service,
        )
    )

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
        deposit_amount=deposit_amount,
        subscription=subscription,
    )
    payment = await get_payment_for_appointment(session, appointment.id)
    return PublicAppointmentResponse(
        id=appointment.id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        status=appointment.status,
        service_name=service.name,
        collaborator_name=professional.full_name,
        deposit_amount=appointment.deposit_amount,
        used_subscription=appointment.subscription_id is not None,
        payment=payment_response(payment) if payment is not None else None,
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

    now = datetime.now(UTC)
    latest = await get_latest_subscription(session, client_id=client.id)
    if latest is not None:
        if latest.status == ClientSubscriptionStatus.ACTIVE:
            raise PublicBookingConflictError("Você já possui uma assinatura ativa.")
        pending = await get_payment_for_subscription(session, latest.id)
        if (
            pending is not None
            and pending.status == PaymentStatus.PENDING
            and pending.expires_at > now
        ):
            raise PublicBookingConflictError(
                "Você já possui uma assinatura aguardando pagamento."
            )
        if pending is not None and pending.status == PaymentStatus.PENDING:
            pending.status = PaymentStatus.EXPIRED
        latest.status = ClientSubscriptionStatus.EXPIRED
        await session.flush()

    try:
        subscription = await create_client_subscription(
            session,
            tenant_id=tenant_id,
            client=client,
            plan_id=plan_id,
            status=ClientSubscriptionStatus.PENDING_PAYMENT,
            now=now,
            commit=False,
        )
    except SubscriptionConflictError as exc:
        raise PublicBookingConflictError(
            "Você já possui uma assinatura ativa."
        ) from exc
    except SubscriptionNotFoundError as exc:
        raise PublicBookingError("Plano inválido") from exc

    if subscription.plan.price <= 0:
        subscription.status = ClientSubscriptionStatus.ACTIVE
        await session.commit()
        await set_tenant_context(session, tenant_id)
        return await public_subscription_response(session, subscription)

    payment = await create_payment_intent(
        session,
        tenant_id=tenant_id,
        client_id=client.id,
        amount=subscription.plan.price,
        expires_at=now
        + timedelta(minutes=settings.payment_subscription_ttl_minutes),
        subscription_id=subscription.id,
    )
    await session.commit()
    await set_tenant_context(session, tenant_id)
    return await public_subscription_response(
        session,
        subscription,
        payment_response(payment),
    )


async def public_get_payment(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
    payment_id: UUID,
) -> PublicPaymentConfirmResponse:
    """Consulta o status do próprio pagamento (polling do link)."""
    tenant_id, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    client = await _client_by_phone(session, phone)
    payment = await get_payment(session, payment_id)
    if client is None or payment is None or payment.client_id != client.id:
        raise PaymentNotFoundError

    if (
        payment.status == PaymentStatus.PENDING
        and payment.expires_at <= datetime.now(UTC)
    ):
        await expire_payment(session, payment)
        await session.commit()
        await set_tenant_context(session, tenant_id)

    data = payment_response(payment)
    return PublicPaymentConfirmResponse(**data.model_dump())


async def public_confirm_mock_payment(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    token: str,
    payment_id: UUID,
) -> PublicPaymentConfirmResponse:
    """Confirma o Pix no provider mock, com checagem de dono e expiração."""
    if settings.payment_provider != "mock":
        raise PaymentNotFoundError

    tenant_id, phone = await _validate_magic(
        session,
        redis,
        slug=slug,
        token=token,
    )
    client = await _client_by_phone(session, phone)
    payment = await get_payment(session, payment_id)
    if client is None or payment is None or payment.client_id != client.id:
        raise PaymentNotFoundError

    if payment.status == PaymentStatus.PAID:
        appointment = (
            await session.get(Appointment, payment.appointment_id)
            if payment.appointment_id is not None
            else None
        )
        subscription = (
            await session.get(ClientSubscription, payment.subscription_id)
            if payment.subscription_id is not None
            else None
        )
        data = payment_response(payment)
        return PublicPaymentConfirmResponse(
            **data.model_dump(),
            appointment_status=(
                appointment.status if appointment is not None else None
            ),
            subscription_status=(
                subscription.status if subscription is not None else None
            ),
        )

    if payment.status != PaymentStatus.PENDING:
        raise PublicBookingConflictError("Pagamento indisponível")

    now = datetime.now(UTC)
    if payment.expires_at <= now:
        await expire_payment(session, payment)
        await session.commit()
        await set_tenant_context(session, tenant_id)
        raise PublicBookingConflictError("Pagamento expirado")

    if payment.appointment_id is not None:
        appointment = await session.get(Appointment, payment.appointment_id)
        if appointment is None or appointment.status not in (
            AppointmentStatus.PENDING_DEPOSIT,
            AppointmentStatus.CONFIRMED,
        ):
            raise PublicBookingConflictError("Pagamento indisponível")

    appointment, subscription = await confirm_payment(
        session,
        payment,
        now=now,
    )
    await session.commit()
    await set_tenant_context(session, tenant_id)
    data = payment_response(payment)
    return PublicPaymentConfirmResponse(
        **data.model_dump(),
        appointment_status=(
            appointment.status if appointment is not None else None
        ),
        subscription_status=(
            subscription.status if subscription is not None else None
        ),
    )
