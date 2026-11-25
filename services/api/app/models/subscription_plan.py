"""Modelos de planos de assinatura."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.service import Service


class BillingCycle(enum.StrEnum):
    """Periodicidade de cobrança do plano."""

    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class SubscriptionPlan(Base):
    """Plano recorrente (clube de assinatura) da clínica."""

    __tablename__ = "subscription_plans"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_subscription_plans_price"),
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle", native_enum=True),
        nullable=False,
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
    items: Mapped[list["SubscriptionPlanItem"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SubscriptionPlanItem(Base):
    """Cota de serviço incluída em um plano de assinatura."""

    __tablename__ = "subscription_plan_items"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "service_id",
            name="uq_subscription_plan_items_plan_id_service_id",
        ),
        CheckConstraint(
            "uses_per_cycle >= 1",
            name="ck_subscription_plan_items_uses_per_cycle",
        ),
        CheckConstraint(
            "min_interval_days IS NULL OR min_interval_days >= 0",
            name="ck_subscription_plan_items_min_interval_days",
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
    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uses_per_cycle: Mapped[int] = mapped_column(nullable=False)
    min_interval_days: Mapped[int | None] = mapped_column(nullable=True)
    allowed_weekdays: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="items")
    service: Mapped["Service"] = relationship("Service", lazy="selectin")
