"""Notas fiscais de serviço (NFS-e) e adapter fiscal."""

import enum
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FiscalInvoiceStatus(enum.StrEnum):
    """Estado da nota fiscal."""

    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class FiscalInvoice(Base):
    """NFS-e emitida para uma comanda."""

    __tablename__ = "fiscal_invoices"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sale_id",
            name="uq_fiscal_invoices_tenant_id_sale_id",
        ),
        CheckConstraint("amount >= 0", name="ck_fiscal_invoices_amount"),
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
    sale_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[FiscalInvoiceStatus] = mapped_column(
        Enum(
            FiscalInvoiceStatus,
            name="fiscal_invoice_status",
            native_enum=True,
        ),
        nullable=False,
        default=FiscalInvoiceStatus.ISSUED,
        server_default=text("'ISSUED'"),
    )
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="mock",
        server_default=text("'mock'"),
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
