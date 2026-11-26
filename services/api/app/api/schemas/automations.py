"""Contratos de automações e execuções."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import AutomationRunStatus, AutomationTrigger


class AutomationRuleResponse(BaseModel):
    """Régua configurada pelo tenant."""

    id: UUID
    trigger: AutomationTrigger
    name: str
    template: str
    delay_minutes: int
    is_active: bool


class AutomationRuleUpdateRequest(BaseModel):
    """Atualização permitida na régua."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    template: str | None = Field(default=None, min_length=1, max_length=4000)
    is_active: bool | None = None


class AutomationRunResponse(BaseModel):
    """Log de execução."""

    id: UUID
    rule_id: UUID
    client_id: UUID
    appointment_id: UUID | None
    status: AutomationRunStatus
    scheduled_for: datetime
    sent_at: datetime | None
    error: str | None
    created_at: datetime


class AutomationRunSummary(BaseModel):
    """Resumo da execução manual/worker."""

    processed: int
    sent: int
    failed: int
    skipped: int
