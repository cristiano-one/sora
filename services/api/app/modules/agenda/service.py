"""Motor de agenda: locks, anti-conflito, RBAC e disponibilidade."""

from datetime import UTC, date, datetime, time, timedelta
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from app.api.schemas.agenda import AvailabilityResponse
from app.core.auth.dependencies import Principal
from app.core.config import settings
from app.core.locks import acquire_lock, release_lock
from app.core.redis import tenant_key
from app.models import (
    Appointment,
    AppointmentStatus,
    Client,
    Service,
    User,
    UserRole,
)
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

WORKDAY_START = time(8, 0)
WORKDAY_END = time(19, 0)
SLOT_STEP_MINUTES = 30
LOCK_TTL_SECONDS = 10
BLOCKED_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.EXPIRED)


class InvalidAppointmentError(Exception):
    """Dados/estado inválidos para o agendamento."""


class SlotUnavailableError(Exception):
    """Horário indisponível (anti-double-booking)."""


class AgendaBusyError(Exception):
    """Outra requisição está reservando a mesma agenda."""


class ForbiddenAgendaError(Exception):
    """COLLABORATOR tentando operar a agenda de outro profissional."""


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

    collaborator = await _resolve_collaborator(
        session,
        principal=principal,
        collaborator_id=collaborator_id,
    )
    client = await _resolve_client(session, client_id)
    service = await _resolve_service(session, service_id)

    ends_at = start + timedelta(minutes=_total_minutes(service))
    lock_key = _lock_key(
        tenant_id=principal.tenant_id,
        collaborator_id=collaborator.id,
        starts_at=start,
    )
    token = await acquire_lock(redis, lock_key, ttl_seconds=LOCK_TTL_SECONDS)
    if token is None:
        raise AgendaBusyError

    try:
        requires_deposit = service.requires_deposit
        appointment = Appointment(
            tenant_id=principal.tenant_id,
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
            deposit_amount=service.deposit_amount if requires_deposit else None,
            notes=notes,
            created_by=principal.user_id,
            client=client,
            service=service,
            collaborator=collaborator,
        )
        session.add(appointment)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if _is_overlap_conflict(exc):
                raise SlotUnavailableError from exc
            raise
        return appointment
    finally:
        await release_lock(redis, lock_key, token)


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
            if "notes" in changes:
                appointment.notes = cast(str | None, changes["notes"])
            await session.commit()
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
    if "notes" in changes:
        appointment.notes = cast(str | None, changes["notes"])
    await session.commit()
    return appointment


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
    total = _total_minutes(service)
    tz = ZoneInfo(settings.default_tenant_timezone)

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
