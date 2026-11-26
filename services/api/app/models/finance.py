"""Contas e lançamentos financeiros do tenant."""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccountType(enum.StrEnum):
    """Tipo de conta/caixa."""

    CASH = "CASH"
    BANK = "BANK"


class FinancialEntryType(enum.StrEnum):
    """Entrada ou saída financeira."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class FinancialEntryStatus(enum.StrEnum):
    """Status do lançamento (previsto vs realizado)."""

    PENDING = "PENDING"
    PAID = "PAID"


class FinancialCategory(enum.StrEnum):
    """Categoria usada no fluxo de caixa e na DRE."""

    SERVICE = "SERVICE"
    PACKAGE = "PACKAGE"
    SUBSCRIPTION = "SUBSCRIPTION"
    PRODUCT = "PRODUCT"
    OTHER_INCOME = "OTHER_INCOME"
    TAX = "TAX"
    CARD_FEE = "CARD_FEE"
    SUPPLIES = "SUPPLIES"
    COMMISSION = "COMMISSION"
    RENT = "RENT"
    UTILITY = "UTILITY"
    MARKETING = "MARKETING"
    PAYROLL = "PAYROLL"
    OTHER_EXPENSE = "OTHER_EXPENSE"


class FinancialAccount(Base):
    """Conta bancária ou caixa físico da clínica."""

    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_financial_accounts_tenant_id_name",
        ),
        CheckConstraint(
            "initial_balance >= 0",
            name="ck_financial_accounts_initial_balance",
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type", native_enum=True),
        nullable=False,
    )
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FinancialEntry(Base):
    """Lançamento financeiro por competência e caixa."""

    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_financial_entries_amount"),
        CheckConstraint(
            "status <> 'PAID' OR cash_date IS NOT NULL",
            name="ck_financial_entries_paid_cash_date",
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
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("financial_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[FinancialEntryType] = mapped_column(
        Enum(
            FinancialEntryType,
            name="financial_entry_type",
            native_enum=True,
        ),
        nullable=False,
    )
    category: Mapped[FinancialCategory] = mapped_column(
        Enum(
            FinancialCategory,
            name="financial_category",
            native_enum=True,
        ),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    competence_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cash_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
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
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    account: Mapped[FinancialAccount] = relationship(
        "FinancialAccount",
        lazy="selectin",
    )
