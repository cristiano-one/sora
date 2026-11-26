"""Modelos de folha de pagamento, adiantamentos e pró-labore."""

import enum
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.finance import FinancialEntryStatus


class PayrollKind(enum.StrEnum):
    """Tipos de verba de folha."""

    SALARY = "SALARY"
    ADVANCE = "ADVANCE"
    PRO_LABORE = "PRO_LABORE"
    COMMISSION_PAYOUT = "COMMISSION_PAYOUT"


class PayrollEntry(Base):
    """Verba de folha vinculada a um usuário da clínica."""

    __tablename__ = "payroll_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payroll_entries_amount"),
        CheckConstraint(
            "status != 'PAID' OR cash_date IS NOT NULL",
            name="ck_payroll_entries_paid_cash_date",
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
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    competence_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[FinancialEntryStatus] = mapped_column(
        Enum(
            FinancialEntryStatus,
            name="financial_entry_status",
            native_enum=True,
        ),
        nullable=False,
        default=FinancialEntryStatus.PENDING,
        server_default=text("'PENDING'"),
        index=True,
    )
    cash_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    financial_entry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("financial_entries.id", ondelete="SET NULL"),
        nullable=True,
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
