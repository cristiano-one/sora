"""Contratos de clientes, score, LGPD, prontuário e anexos."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ClientScoreRating


class ClientCreateRequest(BaseModel):
    """Cadastro de cliente."""

    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr | None = None
    birth_date: date | None = None
    address_zip: str | None = Field(
        default=None,
        max_length=9,
        pattern=r"^\d{5}-?\d{3}$",
    )
    address_street: str | None = Field(default=None, max_length=255)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=120)
    address_neighborhood: str | None = Field(default=None, max_length=120)
    address_city: str | None = Field(default=None, max_length=120)
    address_state: str | None = Field(
        default=None,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )
    notes: str | None = Field(default=None, max_length=5000)


class ClientUpdateRequest(BaseModel):
    """Atualização parcial de cliente (ADMIN/OWNER)."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    email: EmailStr | None = None
    birth_date: date | None = None
    address_zip: str | None = Field(
        default=None,
        max_length=9,
        pattern=r"^\d{5}-?\d{3}$",
    )
    address_street: str | None = Field(default=None, max_length=255)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=120)
    address_neighborhood: str | None = Field(default=None, max_length=120)
    address_city: str | None = Field(default=None, max_length=120)
    address_state: str | None = Field(
        default=None,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )
    notes: str | None = Field(default=None, max_length=5000)
    score: int | None = Field(default=None, ge=0, le=100)
    is_blocked: bool | None = None


class ClientResponse(BaseModel):
    """Cliente para uso interno (telefone mascarado para COLLABORATOR)."""

    id: UUID
    tenant_id: UUID
    full_name: str
    phone: str
    email: str | None
    birth_date: date | None
    address_zip: str | None
    address_street: str | None
    address_number: str | None
    address_complement: str | None
    address_neighborhood: str | None
    address_city: str | None
    address_state: str | None
    notes: str | None
    score: int
    is_blocked: bool


class ScoreEventCreateRequest(BaseModel):
    """Avaliação pós-atendimento."""

    rating: ClientScoreRating
    notes: str | None = Field(default=None, max_length=2000)


class ScoreEventResponse(BaseModel):
    """Resultado da avaliação no score."""

    id: UUID
    client_id: UUID
    rating: ClientScoreRating
    score_after: int


class ConsentCreateRequest(BaseModel):
    """Registro de consentimento LGPD."""

    terms_version: str = Field(min_length=1, max_length=50)
    purposes: list[str] | None = Field(default=None, max_length=10)


class ConsentResponse(BaseModel):
    """Consentimento registrado."""

    id: UUID
    client_id: UUID
    accepted_at: datetime
    terms_version: str
    purposes: list[str] | None


class MedicalRecordCreateRequest(BaseModel):
    """Evolução clínica do prontuário."""

    title: str = Field(min_length=2, max_length=255)
    notes: str = Field(min_length=1, max_length=10000)


class AttachmentResponse(BaseModel):
    """Metadados de anexo (sem URL permanente)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class MedicalRecordResponse(BaseModel):
    """Prontuário com notas decifradas e anexos."""

    id: UUID
    client_id: UUID
    title: str
    notes: str
    created_by: UUID | None
    created_at: datetime
    attachments: list[AttachmentResponse]


class AttachmentPresignRequest(BaseModel):
    """Solicitação de URL pré-assinada de upload."""

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=1, le=10 * 1024 * 1024)


class AttachmentPresignResponse(BaseModel):
    """URL temporária de upload (TTL 60s)."""

    attachment_id: UUID
    upload_url: str
    expires_in: int


class AttachmentUrlResponse(BaseModel):
    """URL temporária de leitura (TTL 60s)."""

    url: str
    expires_in: int


class ClientCreditResponse(BaseModel):
    """Crédito promocional com saldo restante."""

    id: UUID
    amount: Decimal
    used_amount: Decimal
    remaining_amount: Decimal
    reason: str
    reference: str
    expires_at: date
    is_available: bool


class ClientCreditUsageCreateRequest(BaseModel):
    """Aplicação de crédito no atendimento/comanda."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    appointment_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class ClientCreditUsageResponse(BaseModel):
    """Histórico de uso do crédito."""

    id: UUID
    credit_id: UUID
    amount: Decimal
    appointment_id: UUID | None
    note: str | None
    created_at: datetime
