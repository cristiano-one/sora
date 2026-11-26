"""Contratos da conexão WhatsApp Business via Embedded Signup."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import (
    WhatsAppConnectionStatus,
    WhatsAppRegistrationStatus,
)


class WhatsAppEmbeddedSignupConfig(BaseModel):
    """Identificadores públicos usados pelo SDK do Facebook no navegador."""

    enabled: bool
    app_id: str | None
    config_id: str | None
    graph_version: str


class WhatsAppConnectionResponse(BaseModel):
    """Estado da conexão do tenant, sem qualquer token de acesso."""

    status: WhatsAppConnectionStatus
    display_phone_number: str | None
    verified_name: str | None
    quality_rating: str | None
    waba_id: str | None
    phone_number_id: str | None
    registration_status: WhatsAppRegistrationStatus
    registration_error: str | None
    connected_at: datetime | None
    last_error: str | None
    embedded_signup: WhatsAppEmbeddedSignupConfig


class WhatsAppConnectRequest(BaseModel):
    """Dados retornados pelo Embedded Signup após o login na Meta."""

    code: str = Field(min_length=10, max_length=4096)
    waba_id: str = Field(min_length=5, max_length=64, pattern=r"^[0-9]+$")
    phone_number_id: str = Field(
        min_length=5,
        max_length=64,
        pattern=r"^[0-9]+$",
    )
    pin: str = Field(pattern=r"^[0-9]{6}$")
