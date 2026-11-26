"""Modelos de usuário e papéis RBAC."""

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(enum.StrEnum):
    """Papéis RBAC disponíveis no sistema."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    COLLABORATOR = "COLLABORATOR"


class CommissionBase(enum.StrEnum):
    """Base de cálculo da comissão do colaborador."""

    GROSS = "GROSS"
    NET = "NET"


class EmploymentType(enum.StrEnum):
    """Vínculo trabalhista/fiscal do profissional."""

    EMPLOYEE = "EMPLOYEE"
    PARTNER = "PARTNER"
    MEI = "MEI"


class User(Base):
    """Usuário interno vinculado a um tenant."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),
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
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        nullable=False,
    )
    commission_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    commission_fixed: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    commission_base: Mapped[CommissionBase] = mapped_column(
        Enum(CommissionBase, name="commission_base", native_enum=True),
        nullable=False,
        default=CommissionBase.GROSS,
        server_default=text("'GROSS'"),
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type", native_enum=True),
        nullable=False,
        default=EmploymentType.EMPLOYEE,
        server_default=text("'EMPLOYEE'"),
    )
    can_manage_ai_inbox: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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
