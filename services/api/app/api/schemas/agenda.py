"""Contratos de agenda e disponibilidade."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import AppointmentStatus


class AppointmentCreateRequest(BaseModel):
    """Novo agendamento."""

    client_id: UUID
    service_id: UUID
    collaborator_id: UUID | None = None
    starts_at: datetime
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentUpdateRequest(BaseModel):
    """Reagendamento/cancelamento/status."""

    starts_at: datetime | None = None
    status: AppointmentStatus | None = None
    collaborator_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(BaseModel):
    """Agendamento para a agenda interna."""

    id: UUID
    tenant_id: UUID
    collaborator_id: UUID
    client_id: UUID
    service_id: UUID
    client_name: str
    service_name: str
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    deposit_amount: Decimal | None
    subscription_id: UUID | None


class AvailabilityResponse(BaseModel):
    """Horários livres — nunca revela agendamentos de terceiros."""

    collaborator_id: UUID
    service_id: UUID
    date: date
    duration_minutes: int
    buffer_minutes: int
    available: bool
    available_slots: list[str]
