"""Endpoints de agenda: agendamentos e disponibilidade."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.agenda import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentUpdateRequest,
    AvailabilityResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_current_principal,
    get_tenant_session,
)
from app.core.config import settings
from app.core.redis import get_redis
from app.models import Appointment
from app.modules.agenda.service import (
    AgendaBusyError,
    ForbiddenAgendaError,
    InvalidAppointmentError,
    SlotUnavailableError,
    availability,
    create_appointment,
    get_appointment,
    list_appointments,
    update_appointment,
)

router = APIRouter(tags=["agenda"])


def _map_agenda_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ForbiddenAgendaError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )
    if isinstance(exc, (AgendaBusyError, SlotUnavailableError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horário indisponível",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


def _appointment_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        tenant_id=appointment.tenant_id,
        collaborator_id=appointment.collaborator_id,
        client_id=appointment.client_id,
        service_id=appointment.service_id,
        client_name=appointment.client.full_name,
        service_name=appointment.service.name,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        status=appointment.status,
        deposit_amount=appointment.deposit_amount,
    )


def _day_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo de datas inválido",
        )
    if (to_date - from_date).days > 31:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Intervalo máximo de 31 dias",
        )
    tz = ZoneInfo(settings.default_tenant_timezone)
    start = datetime.combine(from_date, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(
        to_date + timedelta(days=1),
        time.min,
        tzinfo=tz,
    ).astimezone(UTC)
    return start, end


@router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria agendamento",
)
async def create_appointment_endpoint(
    body: AppointmentCreateRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
    redis: Redis = Depends(get_redis),
) -> AppointmentResponse:
    try:
        appointment = await create_appointment(
            session,
            redis,
            principal=principal,
            client_id=body.client_id,
            service_id=body.service_id,
            collaborator_id=body.collaborator_id,
            starts_at=body.starts_at,
            notes=body.notes,
        )
    except (
        InvalidAppointmentError,
        ForbiddenAgendaError,
        AgendaBusyError,
        SlotUnavailableError,
    ) as exc:
        raise _map_agenda_error(exc) from exc

    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="appointment.create",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=client_ip(request),
        details={
            "client_id": str(appointment.client_id),
            "service_id": str(appointment.service_id),
        },
    )
    return _appointment_response(appointment)


@router.get(
    "/appointments",
    response_model=list[AppointmentResponse],
    summary="Lista agendamentos por período",
)
async def list_appointments_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    collaborator_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AppointmentResponse]:
    from_dt, to_dt = _day_bounds(from_date, to_date)
    appointments = await list_appointments(
        session,
        principal=principal,
        from_dt=from_dt,
        to_dt=to_dt,
        collaborator_id=collaborator_id,
    )
    return [_appointment_response(appointment) for appointment in appointments]


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Retorna agendamento",
)
async def get_appointment_endpoint(
    appointment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> AppointmentResponse:
    appointment = await get_appointment(
        session,
        principal=principal,
        appointment_id=appointment_id,
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado",
        )
    return _appointment_response(appointment)


@router.patch(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Reagenda, cancela ou atualiza status",
)
async def update_appointment_endpoint(
    appointment_id: UUID,
    body: AppointmentUpdateRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
    redis: Redis = Depends(get_redis),
) -> AppointmentResponse:
    appointment = await get_appointment(
        session,
        principal=principal,
        appointment_id=appointment_id,
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado",
        )

    try:
        updated = await update_appointment(
            session,
            redis,
            principal=principal,
            appointment=appointment,
            changes=body.model_dump(exclude_unset=True),
        )
    except (
        InvalidAppointmentError,
        ForbiddenAgendaError,
        AgendaBusyError,
        SlotUnavailableError,
    ) as exc:
        raise _map_agenda_error(exc) from exc

    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="appointment.update",
        resource_type="appointment",
        resource_id=updated.id,
        ip_address=client_ip(request),
        details={"status": updated.status.value},
    )
    return _appointment_response(updated)


@router.get(
    "/agenda/availability",
    response_model=AvailabilityResponse,
    summary="Retorna horários livres do profissional",
)
async def availability_endpoint(
    service_id: UUID = Query(...),
    day: date = Query(..., alias="date"),
    collaborator_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> AvailabilityResponse:
    try:
        return await availability(
            session,
            principal=principal,
            service_id=service_id,
            collaborator_id=collaborator_id,
            day=day,
        )
    except (InvalidAppointmentError, ForbiddenAgendaError) as exc:
        raise _map_agenda_error(exc) from exc
