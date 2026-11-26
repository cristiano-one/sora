"""Créditos promocionais de clientes (aniversário etc.)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClientCredit(Base):
    """Crédito interno do cliente, com validade e controle de uso."""

    __tablename__ = "client_credits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_client_credits_amount"),
        CheckConstraint(
            "used_amount >= 0 AND used_amount <= amount",
            name="ck_client_credits_used_amount",
        ),
        UniqueConstraint(
            "tenant_id",
            "client_id",
            "reason",
            "reference",
            name="uq_client_credits_tenant_client_reason_reference",
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
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    used_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="BIRTHDAY",
        server_default=text("'BIRTHDAY'"),
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
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

    client = relationship("Client", lazy="selectin")
