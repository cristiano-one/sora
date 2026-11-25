"""Endpoints de clientes, score, LGPD, prontuário e anexos."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.clients import (
    AttachmentPresignRequest,
    AttachmentPresignResponse,
    AttachmentResponse,
    AttachmentUrlResponse,
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
    ConsentCreateRequest,
    ConsentResponse,
    MedicalRecordCreateRequest,
    MedicalRecordResponse,
    ScoreEventCreateRequest,
    ScoreEventResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_current_principal,
    get_tenant_session,
    require_roles,
)
from app.core.config import settings
from app.core.crypto import decrypt_text
from app.core.formatting import mask_phone
from app.core.storage import StoragePort, get_storage
from app.models import Client, MedicalRecord, MedicalRecordAttachment, UserRole
from app.modules.clients.service import (
    InvalidAttachmentError,
    add_consent,
    add_score_event,
    create_attachment,
    create_client,
    create_medical_record,
    update_client,
)

router = APIRouter(prefix="/clients", tags=["clients"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


def _client_response(client: Client, role: UserRole) -> ClientResponse:
    phone = (
        client.phone
        if role in (UserRole.OWNER, UserRole.ADMIN)
        else mask_phone(client.phone)
    )
    return ClientResponse(
        id=client.id,
        tenant_id=client.tenant_id,
        full_name=client.full_name,
        phone=phone,
        email=client.email,
        birth_date=client.birth_date,
        score=client.score,
        is_blocked=client.is_blocked,
    )


def _record_response(record: MedicalRecord) -> MedicalRecordResponse:
    return MedicalRecordResponse(
        id=record.id,
        client_id=record.client_id,
        title=record.title,
        notes=decrypt_text(record.notes_encrypted),
        created_by=record.created_by,
        created_at=record.created_at,
        attachments=[
            AttachmentResponse.model_validate(attachment)
            for attachment in record.attachments
        ],
    )


async def _get_client(session: AsyncSession, client_id: UUID) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return client


async def _get_record(
    session: AsyncSession,
    *,
    client_id: UUID,
    record_id: UUID,
) -> MedicalRecord:
    record = await session.get(MedicalRecord, record_id)
    if record is None or record.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prontuário não encontrado",
        )
    return record


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra cliente",
)
async def create_client_endpoint(
    body: ClientCreateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> ClientResponse:
    client = await create_client(
        session,
        tenant_id=principal.tenant_id,
        body=body,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="client.create",
        resource_type="client",
        resource_id=client.id,
        ip_address=client_ip(request),
    )
    return _client_response(client, principal.role)


@router.get(
    "",
    response_model=list[ClientResponse],
    summary="Lista clientes do tenant",
)
async def list_clients(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[ClientResponse]:
    result = await session.scalars(select(Client).order_by(Client.full_name))
    return [_client_response(client, principal.role) for client in result.all()]


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Retorna cliente",
)
async def get_client_endpoint(
    client_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> ClientResponse:
    client = await _get_client(session, client_id)
    return _client_response(client, principal.role)


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Atualiza cliente (ADMIN/OWNER)",
)
async def update_client_endpoint(
    client_id: UUID,
    body: ClientUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> ClientResponse:
    client = await _get_client(session, client_id)
    updated = await update_client(
        session,
        client=client,
        changes=body.model_dump(exclude_unset=True),
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="client.update",
        resource_type="client",
        resource_id=updated.id,
        ip_address=client_ip(request),
    )
    return _client_response(updated, principal.role)


@router.post(
    "/{client_id}/score-events",
    response_model=ScoreEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Avalia o cliente pós-atendimento",
)
async def create_score_event_endpoint(
    client_id: UUID,
    body: ScoreEventCreateRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> ScoreEventResponse:
    client = await _get_client(session, client_id)
    event = await add_score_event(
        session,
        client=client,
        actor=principal,
        rating=body.rating,
        notes=body.notes,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="client.score",
        resource_type="client",
        resource_id=client.id,
        ip_address=client_ip(request),
        details={"rating": body.rating.value},
    )
    return ScoreEventResponse(
        id=event.id,
        client_id=client.id,
        rating=event.rating,
        score_after=client.score,
    )


@router.post(
    "/{client_id}/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra consentimento LGPD",
)
async def create_consent_endpoint(
    client_id: UUID,
    body: ConsentCreateRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> ConsentResponse:
    client = await _get_client(session, client_id)
    consent = await add_consent(
        session,
        client=client,
        terms_version=body.terms_version,
        purposes=body.purposes,
        ip_address=client_ip(request),
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="client.consent",
        resource_type="client",
        resource_id=client.id,
        ip_address=client_ip(request),
        details={"terms_version": body.terms_version},
    )
    return ConsentResponse(
        id=consent.id,
        client_id=consent.client_id,
        accepted_at=consent.accepted_at,
        terms_version=consent.terms_version,
        purposes=consent.purposes,
    )


@router.post(
    "/{client_id}/records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria evolução do prontuário",
)
async def create_record_endpoint(
    client_id: UUID,
    body: MedicalRecordCreateRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> MedicalRecordResponse:
    client = await _get_client(session, client_id)
    record = await create_medical_record(
        session,
        client=client,
        actor=principal,
        title=body.title,
        notes=body.notes,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="medical_record.create",
        resource_type="medical_record",
        resource_id=record.id,
        ip_address=client_ip(request),
        details={"client_id": str(client.id)},
    )
    return _record_response(record)


@router.get(
    "/{client_id}/records",
    response_model=list[MedicalRecordResponse],
    summary="Lista prontuários do cliente",
)
async def list_records_endpoint(
    client_id: UUID,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[MedicalRecordResponse]:
    client = await _get_client(session, client_id)
    records = (
        await session.scalars(
            select(MedicalRecord)
            .where(MedicalRecord.client_id == client.id)
            .order_by(MedicalRecord.created_at.desc())
        )
    ).all()
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="medical_record.list",
        resource_type="medical_record",
        resource_id=client.id,
        ip_address=client_ip(request),
        details={"client_id": str(client.id)},
    )
    return [_record_response(record) for record in records]


@router.post(
    "/{client_id}/records/{record_id}/attachments/presign",
    response_model=AttachmentPresignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gera URL pré-assinada de upload (60s)",
)
async def presign_attachment_endpoint(
    client_id: UUID,
    record_id: UUID,
    body: AttachmentPresignRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
    storage: StoragePort = Depends(get_storage),
) -> AttachmentPresignResponse:
    client = await _get_client(session, client_id)
    record = await _get_record(
        session,
        client_id=client.id,
        record_id=record_id,
    )
    try:
        attachment = await create_attachment(
            session,
            client=client,
            record=record,
            actor=principal,
            filename=body.filename,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
        )
    except InvalidAttachmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    ttl = settings.storage_presigned_url_ttl_seconds
    upload_url = storage.presign_upload(
        attachment.storage_key,
        attachment.content_type,
        ttl,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="attachment.presign_upload",
        resource_type="attachment",
        resource_id=attachment.id,
        ip_address=client_ip(request),
        details={"client_id": str(client.id), "record_id": str(record.id)},
    )
    return AttachmentPresignResponse(
        attachment_id=attachment.id,
        upload_url=upload_url,
        expires_in=ttl,
    )


@router.get(
    "/{client_id}/records/{record_id}/attachments/{attachment_id}/url",
    response_model=AttachmentUrlResponse,
    summary="Gera URL pré-assinada de leitura (60s)",
)
async def presign_attachment_url_endpoint(
    client_id: UUID,
    record_id: UUID,
    attachment_id: UUID,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
    storage: StoragePort = Depends(get_storage),
) -> AttachmentUrlResponse:
    client = await _get_client(session, client_id)
    record = await _get_record(
        session,
        client_id=client.id,
        record_id=record_id,
    )
    attachment = await session.get(MedicalRecordAttachment, attachment_id)
    if attachment is None or attachment.record_id != record.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não encontrado",
        )

    ttl = settings.storage_presigned_url_ttl_seconds
    url = storage.presign_download(attachment.storage_key, ttl)
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="attachment.view_url",
        resource_type="attachment",
        resource_id=attachment.id,
        ip_address=client_ip(request),
        details={"client_id": str(client.id), "record_id": str(record.id)},
    )
    return AttachmentUrlResponse(url=url, expires_in=ttl)
