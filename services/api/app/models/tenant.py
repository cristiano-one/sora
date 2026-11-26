"""Modelo de tenant (clínica, salão, barbearia ou studio)."""

import enum
from datetime import datetime
from decimal import Decimal
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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaxRegime(enum.StrEnum):
    """Regime tributário simplificado da empresa."""

    MEI = "MEI"
    COMPLETE = "COMPLETE"


class BusinessProfile(enum.StrEnum):
    """Segmento de negócio que define os módulos exibidos."""

    MEDICAL_CLINIC = "MEDICAL_CLINIC"
    AESTHETICS = "AESTHETICS"
    PODOLOGY = "PODOLOGY"
    SALON = "SALON"
    BARBERSHOP = "BARBERSHOP"
    GENERAL = "GENERAL"


MEDICAL_RECORD_PROFILES = frozenset(
    {
        BusinessProfile.MEDICAL_CLINIC,
        BusinessProfile.AESTHETICS,
        BusinessProfile.PODOLOGY,
    }
)


def supports_medical_records(profile: BusinessProfile) -> bool:
    """Indica se o segmento usa prontuário/ficha clínica."""
    return profile in MEDICAL_RECORD_PROFILES


class Tenant(Base):
    """Empresa assinante (tenant) isolada por RLS."""

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tax_regime: Mapped[TaxRegime] = mapped_column(
        Enum(TaxRegime, name="tax_regime", native_enum=True),
        nullable=False,
        default=TaxRegime.COMPLETE,
        server_default=text("'COMPLETE'"),
    )
    business_profile: Mapped[BusinessProfile] = mapped_column(
        Enum(BusinessProfile, name="business_profile", native_enum=True),
        nullable=False,
        default=BusinessProfile.GENERAL,
        server_default=text("'GENERAL'"),
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


class TenantSettings(Base):
    """Configurações de sinal, score e identidade visual da clínica."""

    __tablename__ = "tenant_settings"
    __table_args__ = (
        CheckConstraint(
            "deposit_score_threshold IS NULL OR "
            "(deposit_score_threshold >= 0 AND deposit_score_threshold <= 100)",
            name="ck_tenant_settings_deposit_score_threshold",
        ),
        CheckConstraint(
            "deposit_amount_low_score IS NULL OR deposit_amount_low_score >= 0",
            name="ck_tenant_settings_deposit_amount_low_score",
        ),
        CheckConstraint(
            "theme_primary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tenant_settings_theme_color",
        ),
        CheckConstraint(
            "tithe_percentage >= 0 AND tithe_percentage <= 100",
            name="ck_tenant_settings_tithe_percentage",
        ),
        CheckConstraint(
            "offering_amount >= 0",
            name="ck_tenant_settings_offering_amount",
        ),
        CheckConstraint(
            "birthday_credit_amount >= 0",
            name="ck_tenant_settings_birthday_credit_amount",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    deposit_score_threshold: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    deposit_amount_low_score: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    theme_primary_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#4f46e5",
        server_default=text("'#4f46e5'"),
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Sora",
        server_default=text("'Sora'"),
    )
    agent_tone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="acolhedor",
        server_default=text("'acolhedor'"),
    )
    agent_welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_knowledge: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_cancellation_policy: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    agent_address_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_upsell: Mapped[str | None] = mapped_column(Text, nullable=True)
    fiscal_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    fiscal_provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="mock",
        server_default=text("'mock'"),
    )
    fiscal_municipality: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    fiscal_service_code: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )
    fiscal_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enable_tithe_and_offering: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    tithe_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("10.00"),
        server_default=text("10"),
    )
    offering_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    birthday_credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
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
