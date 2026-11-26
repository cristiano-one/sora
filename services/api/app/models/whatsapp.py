"""Conexão WhatsApp Business (Embedded Signup / Tech Provider) por tenant."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WhatsAppConnectionStatus(enum.StrEnum):
    """Estado da conexão do número da clínica com a Meta."""

    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class WhatsAppRegistrationStatus(enum.StrEnum):
    """Estado do registro do número na Cloud API (PIN de duas etapas)."""

    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TenantWhatsAppAccount(Base):
    """WABA, número e token de acesso da própria clínica.

    O token é sempre armazenado cifrado e nunca retornado pela API. O
    ``phone_number_id`` é único globalmente porque o webhook da Meta chega sem
    JWT e precisa descobrir o tenant por ele.
    """

    __tablename__ = "tenant_whatsapp_accounts"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[WhatsAppConnectionStatus] = mapped_column(
        Enum(
            WhatsAppConnectionStatus,
            name="whatsapp_connection_status",
            native_enum=True,
        ),
        nullable=False,
        default=WhatsAppConnectionStatus.DISCONNECTED,
        server_default=text("'DISCONNECTED'"),
    )
    waba_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_number_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    display_phone_number: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    verified_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    quality_rating: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    access_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    registration_status: Mapped[WhatsAppRegistrationStatus] = mapped_column(
        Enum(
            WhatsAppRegistrationStatus,
            name="whatsapp_registration_status",
            native_enum=False,
            length=20,
            create_constraint=False,
        ),
        nullable=False,
        default=WhatsAppRegistrationStatus.PENDING,
        server_default=text("'PENDING'"),
    )
    registration_error: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    registration_pin_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    registered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    connected_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
