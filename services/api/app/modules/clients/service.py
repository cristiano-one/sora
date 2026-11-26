"""Regras de clientes, score, LGPD e prontuário."""

from pathlib import Path
from uuid import UUID, uuid4

from app.api.schemas.clients import ClientCreateRequest
from app.core.auth.dependencies import Principal
from app.core.crypto import encrypt_text
from app.models import (
    Client,
    ClientScoreEvent,
    ClientScoreRating,
    LgpdConsent,
    MedicalRecord,
    MedicalRecordAttachment,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "application/pdf"})
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


class InvalidAttachmentError(Exception):
    """Tipo ou tamanho de anexo inválido."""


class ClientInUseError(Exception):
    """Cliente possui agendamentos/registros que impedem a exclusão."""


async def create_client(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    body: ClientCreateRequest,
) -> Client:
    """Cria um cliente no tenant atual (RLS já aplicada)."""
    client = Client(
        tenant_id=tenant_id,
        full_name=body.full_name.strip(),
        phone=body.phone.strip(),
        email=str(body.email) if body.email else None,
        birth_date=body.birth_date,
        address_zip=body.address_zip.strip() if body.address_zip else None,
        address_street=(
            body.address_street.strip() if body.address_street else None
        ),
        address_number=(
            body.address_number.strip() if body.address_number else None
        ),
        address_complement=(
            body.address_complement.strip()
            if body.address_complement
            else None
        ),
        address_neighborhood=(
            body.address_neighborhood.strip()
            if body.address_neighborhood
            else None
        ),
        address_city=(
            body.address_city.strip() if body.address_city else None
        ),
        address_state=(
            body.address_state.strip().upper() if body.address_state else None
        ),
        notes_encrypted=(
            encrypt_text(body.notes.strip()) if body.notes else None
        ),
    )
    session.add(client)
    await session.commit()
    return client


async def update_client(
    session: AsyncSession,
    *,
    client: Client,
    changes: dict[str, object],
) -> Client:
    """Aplica alterações parciais no cliente."""
    changes = dict(changes)
    notes_provided = "notes" in changes
    notes = changes.pop("notes", None)
    if notes_provided:
        client.notes_encrypted = (
            encrypt_text(str(notes).strip()) if notes else None
        )
    for field in (
        "full_name",
        "phone",
        "email",
        "birth_date",
        "address_zip",
        "address_street",
        "address_number",
        "address_complement",
        "address_neighborhood",
        "address_city",
        "address_state",
        "score",
        "is_blocked",
    ):
        if field in changes:
            value = changes[field]
            if field == "email" and value is not None:
                value = str(value)
            if field.startswith("address_") and isinstance(value, str):
                value = value.strip()
            if field == "address_state" and isinstance(value, str):
                value = value.upper()
            setattr(client, field, value)
    await session.commit()
    return client


async def delete_client(
    session: AsyncSession,
    *,
    client: Client,
) -> None:
    """Exclui o cliente quando não há agendamentos vinculados."""
    await session.delete(client)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ClientInUseError from exc


async def add_score_event(
    session: AsyncSession,
    *,
    client: Client,
    actor: Principal,
    rating: ClientScoreRating,
    notes: str | None,
) -> ClientScoreEvent:
    """Registra a avaliação e ajusta o score interno (0-100)."""
    delta = 5 if rating == ClientScoreRating.POSITIVE else -10
    client.score = max(0, min(100, client.score + delta))
    event = ClientScoreEvent(
        tenant_id=client.tenant_id,
        client_id=client.id,
        rating=rating,
        notes_encrypted=encrypt_text(notes) if notes else None,
        created_by=actor.user_id,
    )
    session.add(event)
    await session.commit()
    return event


async def add_consent(
    session: AsyncSession,
    *,
    client: Client,
    terms_version: str,
    purposes: list[str] | None,
    ip_address: str | None,
) -> LgpdConsent:
    """Registra o aceite LGPD do cliente."""
    consent = LgpdConsent(
        tenant_id=client.tenant_id,
        client_id=client.id,
        ip_address=ip_address,
        terms_version=terms_version,
        purposes=purposes,
    )
    session.add(consent)
    await session.commit()
    return consent


async def create_medical_record(
    session: AsyncSession,
    *,
    client: Client,
    actor: Principal,
    title: str,
    notes: str,
) -> MedicalRecord:
    """Cria evolução clínica com notas cifradas em repouso."""
    record = MedicalRecord(
        tenant_id=client.tenant_id,
        client_id=client.id,
        title=title.strip(),
        notes_encrypted=encrypt_text(notes),
        created_by=actor.user_id,
        attachments=[],
    )
    session.add(record)
    await session.commit()
    return record


def build_storage_key(
    *,
    tenant_id: UUID,
    client_id: UUID,
    record_id: UUID,
    attachment_id: UUID,
    filename: str,
) -> str:
    """Chave privada e tenant-scoped do objeto no bucket."""
    safe = Path(filename).name or "file"
    return (
        f"tenant/{tenant_id}/clients/{client_id}/records/"
        f"{record_id}/{attachment_id}/{safe}"
    )


async def create_attachment(
    session: AsyncSession,
    *,
    client: Client,
    record: MedicalRecord,
    actor: Principal,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> MedicalRecordAttachment:
    """Cria o metadado do anexo (o upload ocorre via URL pré-assinada)."""
    if content_type not in ALLOWED_MIME_TYPES:
        raise InvalidAttachmentError("Tipo de arquivo não permitido")
    if not 0 < size_bytes <= MAX_ATTACHMENT_SIZE:
        raise InvalidAttachmentError("Tamanho de arquivo inválido")

    attachment_id = uuid4()
    attachment = MedicalRecordAttachment(
        id=attachment_id,
        tenant_id=client.tenant_id,
        record_id=record.id,
        storage_key=build_storage_key(
            tenant_id=client.tenant_id,
            client_id=client.id,
            record_id=record.id,
            attachment_id=attachment_id,
            filename=filename,
        ),
        filename=Path(filename).name or "file",
        content_type=content_type,
        size_bytes=size_bytes,
        created_by=actor.user_id,
    )
    session.add(attachment)
    await session.commit()
    return attachment


async def delete_attachment(
    session: AsyncSession,
    *,
    attachment: MedicalRecordAttachment,
) -> None:
    """Remove o metadado do anexo; o objeto é apagado pelo storage."""
    await session.delete(attachment)
    await session.commit()
