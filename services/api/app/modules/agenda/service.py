"""Motor de agenda: locks, anti-conflito, RBAC e disponibilidade."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from app.api.schemas.agenda import AvailabilityResponse
from app.core.auth.dependencies import Principal
from app.core.config import settings
from app.core.locks import acquire_lock, release_lock
from app.core.redis import tenant_key
from app.db.rls import set_tenant_context
from app.models import (
    Appointment,
    AppointmentStatus,
    Client,
    ClientSubscription,
    Service,
    TenantSettings,
    User,
    UserRole,
)
from app.modules.automations.service import (
    schedule_appointment_automations,
    schedule_post_service,
    skip_pending_for_appointment,
)
from app.modules.payments.service import (
    cancel_pending_payments,
    create_payment_intent,
    expire_pending_payments,
)
from app.modules.subscriptions.service import (
    consume_quota,
    get_active_subscription,
    quota_decision,
    quota_lock_key,
    release_quota,
)
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

WORKDAY_START = time(8, 0)
WORKDAY_END = time(19, 0)
SLOT_STEP_MINUTES = 30
LOCK_TTL_SECONDS = 10
PENDING_DEPOSIT_TTL_MINUTES = 10
BLOCKED_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.EXPIRED)


class InvalidAppointmentError(Exception):
    """Dados/estado inválidos para o agendamento."""


class SlotUnavailableError(Exception):
    """Horário indisponível (anti-double-booking)."""


class AgendaBusyError(Exception):
    """Outra requisição está reservando a mesma agenda."""


class ForbiddenAgendaError(Exception):
    """COLLABORATOR tentando operar a agenda de outro profissional."""


class QuotaUnavailableError(Exception):
    """Cota de assinatura esgotada durante a confirmação."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise InvalidAppointmentError("starts_at deve conter timezone")
    return value.astimezone(UTC)


def _is_overlap_conflict(exc: IntegrityError) -> bool:
    candidates = (exc.orig, getattr(exc.orig, "__cause__", None))
    for candidate in candidates:
        if getattr(candidate, "constraint_name", None) == "ex_appointments_no_overlap":
            return True
    return "ex_appointments_no_overlap" in str(exc.orig)


def _lock_key(
    *,
    tenant_id: UUID,
    collaborator_id: UUID,
    starts_at: datetime,
) -> str:
    return tenant_key(
        tenant_id,
        "agenda",
        "lock",
        str(collaborator_id),
        starts_at.date().isoformat(),
    )


async def _resolve_collaborator(
    session: AsyncSession,
    *,
    principal: Principal,
    collaborator_id: UUID | None,
) -> User:
    target_id = collaborator_id or principal.user_id
    if principal.role == UserRole.COLLABORATOR and target_id != principal.user_id:
        raise ForbiddenAgendaError

    collaborator = await session.get(User, target_id)
    if collaborator is None or not collaborator.is_active:
        raise InvalidAppointmentError("Profissional inválido")
    return collaborator


async def _resolve_client(session: AsyncSession, client_id: UUID) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise InvalidAppointmentError("Cliente inválido")
    if client.is_blocked:
        raise InvalidAppointmentError("Cliente bloqueado para agendamento")
    return client


async def _resolve_service(session: AsyncSession, service_id: UUID) -> Service:
    service = await session.get(Service, service_id)
    if service is None or not service.is_active:
        raise InvalidAppointmentError("Serviço inválido")
    return service


def _total_minutes(service: Service) -> int:
    return service.duration_minutes + service.buffer_minutes


async def resolve_deposit_amount(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    client: Client,
    service: Service,
) -> Decimal | None:
    """Decide o sinal por score baixo ou regra do serviço (nunca expõe motivo)."""
    tenant_settings = await session.get(TenantSettings, tenant_id)
    if (
        tenant_settings is not None
        and tenant_settings.deposit_score_threshold is not None
        and client.score < tenant_settings.deposit_score_threshold
        and tenant_settings.deposit_amount_low_score is not None
        and tenant_settings.deposit_amount_low_score > 0
    ):
        return tenant_settings.deposit_amount_low_score
    if service.requires_deposit:
        return service.deposit_amount
    return None


async def expire_pending_deposits(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> int:
    """Expira reservas com sinal vencido, liberando o horário e a cota."""
    expired = list(
        (
            await session.scalars(
                select(Appointment).where(
                    Appointment.status == AppointmentStatus.PENDING_DEPOSIT,
                    Appointment.deposit_expires_at.is_not(None),
                    Appointment.deposit_expires_at <= datetime.now(UTC),
                )
            )
        ).all()
    )
    if not expired:
        return 0

    for appointment in expired:
        appointment.status = AppointmentStatus.EXPIRED
        await release_quota(session, appointment_id=appointment.id)
    await expire_pending_payments(
        session,
        appointment_ids=[appointment.id for appointment in expired],
    )
    await session.commit()
    # O commit encerra o SET LOCAL do RLS; reaplica para o restante da requisição.
    await set_tenant_context(session, tenant_id)
    return len(expired)


async def _insert_appointment(
    session: AsyncSession,
    redis: Redis,
    *,
    tenant_id: UUID,
    collaborator: User,
    client: Client,
    service: Service,
    start: datetime,
    notes: str | None,
    created_by: UUID | None,
    deposit_amount: Decimal | None = None,
    subscription: ClientSubscription | None = None,
) -> Appointment:
    """Insere com lock Redis + EXCLUDE gist (usado nos fluxos interno e público)."""
    ends_at = start + timedelta(minutes=_total_minutes(service))
    lock_key = _lock_key(
        tenant_id=tenant_id,
        collaborator_id=collaborator.id,
        starts_at=start,
    )
    token = await acquire_lock(redis, lock_key, ttl_seconds=LOCK_TTL_SECONDS)
    if token is None:
        raise AgendaBusyError

    quota_key: str | None = None
    quota_token: str | None = None
    try:
        if subscription is not None:
            quota_key = quota_lock_key(
                tenant_id,
                subscription.id,
                service.id,
            )
            quota_token = await acquire_lock(
                redis,
                quota_key,
                ttl_seconds=LOCK_TTL_SECONDS,
            )
            if quota_token is None:
                raise AgendaBusyError
            decision = await quota_decision(
                session,
                subscription=subscription,
                service_id=service.id,
                starts_at=start,
            )
            if not decision.available:
                raise QuotaUnavailableError

        requires_deposit = deposit_amount is not None and subscription is None
        deposit_expires_at = (
            datetime.now(UTC) + timedelta(minutes=PENDING_DEPOSIT_TTL_MINUTES)
            if requires_deposit
            else None
        )
        appointment = Appointment(
            tenant_id=tenant_id,
            collaborator_id=collaborator.id,
            client_id=client.id,
            service_id=service.id,
            starts_at=start,
            ends_at=ends_at,
            status=(
                AppointmentStatus.PENDING_DEPOSIT
                if requires_deposit
                else AppointmentStatus.SCHEDULED
            ),
            deposit_amount=deposit_amount if requires_deposit else None,
            deposit_expires_at=deposit_expires_at,
            notes=notes,
            created_by=created_by,
            subscription_id=subscription.id if subscription is not None else None,
            client=client,
            service=service,
            collaborator=collaborator,
        )
        session.add(appointment)
        try:
            await session.flush()
            if subscription is not None:
                await consume_quota(
                    session,
                    subscription=subscription,
                    service=service,
                    appointment_id=appointment.id,
                    used_at=start,
                )
            if (
                requires_deposit
                and deposit_amount is not None
                and deposit_expires_at is not None
            ):
                await create_payment_intent(
                    session,
                    tenant_id=tenant_id,
                    client_id=client.id,
                    amount=deposit_amount,
                    expires_at=deposit_expires_at,
                    appointment_id=appointment.id,
                )
            await session.commit()
            await set_tenant_context(session, tenant_id)
            await schedule_appointment_automations(
                session,
                appointment=appointment,
            )
        except IntegrityError as exc:
            await session.rollback()
            if _is_overlap_conflict(exc):
                raise SlotUnavailableError from exc
            raise
        return appointment
    finally:
        if quota_key is not None and quota_token is not None:
            await release_lock(redis, quota_key, quota_token)
        await release_lock(redis, lock_key, token)


async def resolve_quota_subscription(
    session: AsyncSession,
    *,
    client: Client,
    service: Service,
    start: datetime,
) -> ClientSubscription | None:
    """Retorna a assinatura ativa se o serviço tem cota disponível."""
    subscription = await get_active_subscription(
        session,
        client_id=client.id,
        at=start,
    )
    if subscription is None:
        return None
    decision = await quota_decision(
        session,
        subscription=subscription,
        service_id=service.id,
        starts_at=start,
    )
    return subscription if decision.available else None


async def create_appointment(
    session: AsyncSession,
    redis: Redis,
    *,
    principal: Principal,
    client_id: UUID,
    service_id: UUID,
    collaborator_id: UUID | None,
    starts_at: datetime,
    notes: str | None,
) -> Appointment:
    """Cria com lock Redis (nível 1) + EXCLUDE gist (nível 2)."""
    start = _as_utc(starts_at)
    if start <= datetime.now(UTC):
        raise InvalidAppointmentError("starts_at deve estar no futuro")
    await expire_pending_deposits(session, tenant_id=principal.tenant_id)

    collaborator = await _resolve_collaborator(
        session,
        principal=principal,
        collaborator_id=collaborator_id,
    )
    client = await _resolve_client(session, client_id)
    service = await _resolve_service(session, service_id)
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
            tenant_id=principal.tenant_id,
            client=client,
            service=service,
        )
    )

    return await _insert_appointment(
        session,
        redis,
        tenant_id=principal.tenant_id,
        collaborator=collaborator,
        client=client,
        service=service,
        start=start,
        notes=notes,
        created_by=principal.user_id,
        deposit_amount=deposit_amount,
        subscription=subscription,
    )


async def list_appointments(
    session: AsyncSession,
    *,
    principal: Principal,
    from_dt: datetime,
    to_dt: datetime,
    collaborator_id: UUID | None,
) -> list[Appointment]:
    """Lista agendas; COLLABORATOR vê apenas a própria."""
    target_id = collaborator_id
    if principal.role == UserRole.COLLABORATOR:
        target_id = principal.user_id

    statement = (
        select(Appointment)
        .where(
            Appointment.starts_at >= from_dt,
            Appointment.starts_at < to_dt,
        )
        .order_by(Appointment.starts_at)
    )
    if target_id is not None:
        statement = statement.where(Appointment.collaborator_id == target_id)

    result = await session.scalars(statement)
    return list(result.all())


async def get_appointment(
    session: AsyncSession,
    *,
    principal: Principal,
    appointment_id: UUID,
) -> Appointment | None:
    """Busca por id respeitando o escopo do COLLABORATOR."""
    appointment = await session.get(Appointment, appointment_id)
    if appointment is None:
        return None
    if (
        principal.role == UserRole.COLLABORATOR
        and appointment.collaborator_id != principal.user_id
    ):
        return None
    return appointment


async def update_appointment(
    session: AsyncSession,
    redis: Redis,
    *,
    principal: Principal,
    appointment: Appointment,
    changes: dict[str, object],
) -> Appointment:
    """Reagenda/cancela mantendo as duas travas anti-conflito."""
    if (
        principal.role == UserRole.COLLABORATOR
        and appointment.collaborator_id != principal.user_id
    ):
        raise ForbiddenAgendaError

    new_start = changes.get("starts_at")
    new_collaborator_id = changes.get("collaborator_id")

    if new_start is not None or new_collaborator_id is not None:
        if principal.role == UserRole.COLLABORATOR and new_collaborator_id is not None:
            raise ForbiddenAgendaError

        start = (
            _as_utc(new_start)
            if isinstance(new_start, datetime)
            else appointment.starts_at
        )
        if start <= datetime.now(UTC):
            raise InvalidAppointmentError("starts_at deve estar no futuro")

        collaborator = appointment.collaborator
        if new_collaborator_id is not None:
            collaborator = await _resolve_collaborator(
                session,
                principal=principal,
                collaborator_id=cast(UUID, new_collaborator_id),
            )

        ends_at = start + timedelta(minutes=_total_minutes(appointment.service))
        lock_key = _lock_key(
            tenant_id=principal.tenant_id,
            collaborator_id=collaborator.id,
            starts_at=start,
        )
        token = await acquire_lock(redis, lock_key, ttl_seconds=LOCK_TTL_SECONDS)
        if token is None:
            raise AgendaBusyError

        try:
            appointment.starts_at = start
            appointment.ends_at = ends_at
            appointment.collaborator = collaborator
            appointment.collaborator_id = collaborator.id
            if "status" in changes:
                new_status = changes["status"]
                if new_status is not None:
                    appointment.status = cast(AppointmentStatus, new_status)
                    if appointment.status in (
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.EXPIRED,
                    ):
                        await release_quota(
                            session,
                            appointment_id=appointment.id,
                        )
                        await cancel_pending_payments(
                            session,
                            appointment_id=appointment.id,
                        )
            if "notes" in changes:
                appointment.notes = cast(str | None, changes["notes"])
            await session.commit()
            await set_tenant_context(session, appointment.tenant_id)
            if appointment.status in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.EXPIRED,
            ):
                await skip_pending_for_appointment(
                    session,
                    tenant_id=appointment.tenant_id,
                    appointment_id=appointment.id,
                )
            elif appointment.status == AppointmentStatus.COMPLETED:
                await schedule_post_service(
                    session,
                    appointment=appointment,
                )
        except IntegrityError as exc:
            await session.rollback()
            if _is_overlap_conflict(exc):
                raise SlotUnavailableError from exc
            raise
        finally:
            await release_lock(redis, lock_key, token)

        return appointment

    if "status" in changes:
        new_status = changes["status"]
        if new_status is not None:
            appointment.status = cast(AppointmentStatus, new_status)
            if appointment.status in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.EXPIRED,
            ):
                await release_quota(
                    session,
                    appointment_id=appointment.id,
                )
                await cancel_pending_payments(
                    session,
                    appointment_id=appointment.id,
                )
    if "notes" in changes:
        appointment.notes = cast(str | None, changes["notes"])
    await session.commit()
    await set_tenant_context(session, appointment.tenant_id)
    if appointment.status in (
        AppointmentStatus.CANCELLED,
        AppointmentStatus.EXPIRED,
    ):
        await skip_pending_for_appointment(
            session,
            tenant_id=appointment.tenant_id,
            appointment_id=appointment.id,
        )
    elif appointment.status == AppointmentStatus.COMPLETED:
        await schedule_post_service(session, appointment=appointment)
    return appointment


async def _compute_slots(
    session: AsyncSession,
    *,
    collaborator: User,
    service: Service,
    day: date,
) -> AvailabilityResponse:
    """Calcula horários livres (sem expor agendamentos de terceiros)."""
    total = _total_minutes(service)
    tz = ZoneInfo(settings.default_tenant_timezone)
    await expire_pending_deposits(session, tenant_id=collaborator.tenant_id)

    day_start = datetime.combine(day, WORKDAY_START, tzinfo=tz)
    day_end = datetime.combine(day, WORKDAY_END, tzinfo=tz)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)

    result = await session.scalars(
        select(Appointment).where(
            Appointment.collaborator_id == collaborator.id,
            Appointment.starts_at < day_end_utc,
            Appointment.ends_at > day_start_utc,
            Appointment.status.notin_(BLOCKED_STATUSES),
        )
    )
    busy = list(result.all())

    slots: list[str] = []
    slot = day_start
    while slot + timedelta(minutes=total) <= day_end:
        slot_utc = slot.astimezone(UTC)
        if slot_utc <= datetime.now(UTC):
            slot += timedelta(minutes=SLOT_STEP_MINUTES)
            continue
        slot_end = slot_utc + timedelta(minutes=total)
        overlaps = any(
            slot_utc < appointment.ends_at and slot_end > appointment.starts_at
            for appointment in busy
        )
        if not overlaps:
            slots.append(slot.strftime("%H:%M"))
        slot += timedelta(minutes=SLOT_STEP_MINUTES)

    return AvailabilityResponse(
        collaborator_id=collaborator.id,
        service_id=service.id,
        date=day,
        duration_minutes=service.duration_minutes,
        buffer_minutes=service.buffer_minutes,
        available=bool(slots),
        available_slots=slots,
    )


async def availability(
    session: AsyncSession,
    *,
    principal: Principal,
    service_id: UUID,
    collaborator_id: UUID | None,
    day: date,
) -> AvailabilityResponse:
    """Calcula horários livres sem expor agendamentos de terceiros."""
    collaborator = await _resolve_collaborator(
        session,
        principal=principal,
        collaborator_id=collaborator_id,
    )
    service = await _resolve_service(session, service_id)
    return await _compute_slots(
        session,
        collaborator=collaborator,
        service=service,
        day=day,
    )
