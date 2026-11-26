"""Comanda digital, itens e fechamento financeiro."""

import enum
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SaleStatus(enum.StrEnum):
    """Ciclo de vida da comanda."""

    OPEN = "OPEN"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class SaleItemCategory(enum.StrEnum):
    """Categoria comercial do item da comanda."""

    SERVICE = "SERVICE"
    PACKAGE = "PACKAGE"
    PRODUCT = "PRODUCT"
    OTHER = "OTHER"


class SalePaymentMethod(enum.StrEnum):
    """Forma de pagamento registrada na comanda."""

    PIX = "PIX"
    CASH = "CASH"
    CARD = "CARD"
    BOLETO = "BOLETO"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class Sale(Base):
    """Comanda de atendimento com itens, desconto e pagamento."""

    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_sales_subtotal"),
        CheckConstraint("discount >= 0", name="ck_sales_discount"),
        CheckConstraint("credit_amount >= 0", name="ck_sales_credit_amount"),
        CheckConstraint("total >= 0", name="ck_sales_total"),
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
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    collaborator_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    account_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("financial_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    financial_entry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("financial_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[SaleStatus] = mapped_column(
        Enum(SaleStatus, name="sale_status", native_enum=True),
        nullable=False,
        default=SaleStatus.OPEN,
        server_default=text("'OPEN'"),
        index=True,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    payment_method: Mapped[SalePaymentMethod | None] = mapped_column(
        Enum(SalePaymentMethod, name="sale_payment_method", native_enum=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    client = relationship("Client", lazy="selectin")


class SaleItem(Base):
    """Item de serviço, pacote ou produto da comanda."""

    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_items_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_sale_items_unit_price"),
        CheckConstraint("cost >= 0", name="ck_sale_items_cost"),
        CheckConstraint("total >= 0", name="ck_sale_items_total"),
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
    service_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[SaleItemCategory] = mapped_column(
        Enum(SaleItemCategory, name="sale_item_category", native_enum=True),
        nullable=False,
        default=SaleItemCategory.SERVICE,
        server_default=text("'SERVICE'"),
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    sale: Mapped[Sale] = relationship(back_populates="items")
