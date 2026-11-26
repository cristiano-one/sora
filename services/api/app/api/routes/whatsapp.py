"""Conexão WhatsApp Business (Tech Provider) e webhook oficial da Meta."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.whatsapp import (
    WhatsAppConnectionResponse,
    WhatsAppConnectRequest,
    WhatsAppEmbeddedSignupConfig,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.core.config import settings
from app.core.meta_signature import (
    verify_meta_signature,
    verify_meta_verify_token,
)
from app.core.redis import get_redis
from app.db.session import get_session
from app.integrations.meta_whatsapp import MetaWhatsAppError
from app.models import (
    TenantWhatsAppAccount,
    UserRole,
    WhatsAppConnectionStatus,
    WhatsAppRegistrationStatus,
)
from app.modules.agenda.public_service import PublicBookingError
from app.modules.ai.service import AiTenantNotFoundError, handle_tenant_message
from app.modules.whatsapp.service import (
    WhatsAppAlreadyConnectedError,
    WhatsAppConnectionNotFoundError,
    connect_tenant,
    disconnect_tenant,
    get_account,
    resolve_tenant_id_by_phone_number_id,
)
from app.modules.whatsapp.webhook import parse_inbound_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)
_require_owner = require_roles(UserRole.OWNER)


def _connection_response(
    account: TenantWhatsAppAccount | None,
) -> WhatsAppConnectionResponse:
    enabled = bool(
        settings.whatsapp_app_id
        and settings.whatsapp_config_id
        and settings.whatsapp_app_secret
    )
    return WhatsAppConnectionResponse(
        status=(
            account.status
            if account is not None
            else WhatsAppConnectionStatus.DISCONNECTED
        ),
        display_phone_number=(
            account.display_phone_number if account is not None else None
        ),
        verified_name=account.verified_name if account is not None else None,
        quality_rating=(
            account.quality_rating if account is not None else None
        ),
        waba_id=account.waba_id if account is not None else None,
        phone_number_id=(
            account.phone_number_id if account is not None else None
        ),
        registration_status=(
            account.registration_status
            if account is not None
            else WhatsAppRegistrationStatus.PENDING
        ),
        registration_error=(
            account.registration_error if account is not None else None
        ),
        connected_at=account.connected_at if account is not None else None,
        last_error=account.last_error if account is not None else None,
        embedded_signup=WhatsAppEmbeddedSignupConfig(
            enabled=enabled,
            app_id=settings.whatsapp_app_id or None,
            config_id=settings.whatsapp_config_id or None,
            graph_version=settings.whatsapp_graph_version,
        ),
    )


@router.get(
    "/connection",
    response_model=WhatsAppConnectionResponse,
    summary="Estado da conexão WhatsApp da clínica",
)
async def get_connection_endpoint(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> WhatsAppConnectionResponse:
    return _connection_response(
        await get_account(session, principal.tenant_id)
    )


@router.post(
    "/connection",
    response_model=WhatsAppConnectionResponse,
    summary="Conecta o WhatsApp da clínica via Embedded Signup",
)
async def connect_endpoint(
    body: WhatsAppConnectRequest,
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> WhatsAppConnectionResponse:
    try:
        account = await connect_tenant(
            session,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            code=body.code,
            waba_id=body.waba_id,
            phone_number_id=body.phone_number_id,
            pin=body.pin,
        )
    except WhatsAppAlreadyConnectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este número já está conectado em outra clínica.",
        ) from exc
    except MetaWhatsAppError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="whatsapp.connect",
        resource_type="tenant_whatsapp_account",
        resource_id=principal.tenant_id,
        ip_address=client_ip(request),
        details={
            "waba_id": body.waba_id,
            "phone_number_id": body.phone_number_id,
        },
    )
    return _connection_response(account)


@router.delete(
    "/connection",
    response_model=WhatsAppConnectionResponse,
    summary="Desconecta o WhatsApp da clínica",
)
async def disconnect_endpoint(
    request: Request,
    principal: Principal = Depends(_require_owner),
    session: AsyncSession = Depends(get_tenant_session),
) -> WhatsAppConnectionResponse:
    try:
        account = await disconnect_tenant(
            session,
            tenant_id=principal.tenant_id,
        )
    except WhatsAppConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma conexão WhatsApp encontrada.",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="whatsapp.disconnect",
        resource_type="tenant_whatsapp_account",
        resource_id=principal.tenant_id,
        ip_address=client_ip(request),
    )
    return _connection_response(account)


@router.get(
    "/webhook",
    include_in_schema=False,
    summary="Verificação do webhook da Meta",
)
async def verify_webhook_endpoint(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> PlainTextResponse:
    if hub_mode != "subscribe" or not verify_meta_verify_token(
        hub_verify_token,
        settings.whatsapp_verify_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verificação recusada",
        )
    return PlainTextResponse(hub_challenge)


@router.post(
    "/webhook",
    include_in_schema=False,
    summary="Recebe mensagens oficiais do WhatsApp Cloud API",
)
async def receive_webhook_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    raw_body = await request.body()
    if not verify_meta_signature(
        raw_body=raw_body,
        signature_header=request.headers.get("x-hub-signature-256", ""),
        app_secret=settings.whatsapp_app_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assinatura inválida",
        )
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido",
        ) from exc

    for message in parse_inbound_messages(payload):
        tenant_id = await resolve_tenant_id_by_phone_number_id(
            session,
            message.phone_number_id,
        )
        if tenant_id is None:
            logger.info("Webhook WhatsApp sem tenant para o phone_number_id")
            continue
        try:
            await handle_tenant_message(
                session,
                redis,
                tenant_id=tenant_id,
                phone=message.phone,
                text=message.text,
                external_id=message.external_id,
            )
        except (AiTenantNotFoundError, PublicBookingError):
            await session.rollback()
            logger.info("Webhook WhatsApp ignorado para o tenant %s", tenant_id)
        except Exception:
            await session.rollback()
            logger.exception(
                "Falha ao processar webhook WhatsApp (message_id=%s)",
                message.external_id,
            )

    # A Meta exige 200 rápido; falhas de um tenant não devem gerar retry em
    # cascata para os demais.
    return {"status": "ok"}
