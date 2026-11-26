"""Automautomações de relacionamento e execuções agendadas."""

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AutomationTrigger(enum.StrEnum):
    """Gatilhos suportados pelo motor."""

    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    REMINDER_24H = "REMINDER_24H"
    REMINDER_2H = "REMINDER_2H"
    POST_SERVICE = "POST_SERVICE"
    WINBACK_60D = "WINBACK_60D"
    BIRTHDAY = "BIRTHDAY"


class AutomationRunStatus(enum.StrEnum):
    """Estado de uma execução."""

    PENDING = "PENDING"
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class AutomationRule(Base):
    """Régua configurável por tenant."""

    __tablename__ = "automation_rules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "trigger",
            name="uq_automation_rules_tenant_id_trigger",
        ),
        CheckConstraint(
            "delay_minutes >= -10080 AND delay_minutes <= 10080",
            name="ck_automation_rules_delay",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger: Mapped[AutomationTrigger] = mapped_column(
        Enum(
            AutomationTrigger,
            name="automation_trigger",
            native_enum=True,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AutomationRun(Base):
    """Execução agendada de uma régua."""

    __tablename__ = "automation_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "dedupe_key",
            name="uq_automation_runs_tenant_id_dedupe_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[AutomationRunStatus] = mapped_column(
        Enum(
            AutomationRunStatus,
            name="automation_run_status",
            native_enum=True,
        ),
        nullable=False,
        default=AutomationRunStatus.PENDING,
        server_default=text("'PENDING'"),
        index=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
