"""Modelo de tenant (clínica, salão, barbearia ou studio)."""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaxRegime(enum.StrEnum):
    """Regime tributário simplificado da empresa."""

    MEI = "MEI"
    COMPLETE = "COMPLETE"


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
