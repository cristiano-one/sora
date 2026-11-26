"""Endpoints da SORA IA: webhook interno e central de conversas."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.ai import (
    AiConversationDetailResponse,
    AiConversationReplyRequest,
    AiConversationResponse,
    AiMessageResponse,
    AiSummaryResponse,
    BirthdayCreditResponse,
    BirthdayCreditRunResponse,
    WhatsAppWebhookRequest,
    WhatsAppWebhookResponse,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.core.internal_auth import verify_internal_token
from app.core.redis import get_redis
from app.db.session import get_session
from app.models import UserRole
from app.modules.agenda.public_service import PublicBookingError
from app.modules.ai.service import (
    AiApprovalError,
    AiConversationNotFoundError,
    AiTenantNotFoundError,
    ai_summary,
    approve_conversation,
    close_conversation,
    conversation_detail,
    create_birthday_credits,
    handle_whatsapp_message,
    list_birthday_credits,
    list_conversations,
    send_human_message,
    takeover_conversation,
)

router = APIRouter(prefix="/ai", tags=["sora-ai"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.post(
    "/whatsapp/webhook",
    response_model=WhatsAppWebhookResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Recebe mensagem do roteador interno do WhatsApp",
)
async def whatsapp_webhook_endpoint(
    body: WhatsAppWebhookRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> WhatsAppWebhookResponse:
    try:
        return await handle_whatsapp_message(
            session,
            redis,
            tenant_slug=body.tenant_slug,
            phone=body.phone,
            text=body.text,
        )
    except AiTenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clínica não encontrada",
        ) from exc
    except PublicBookingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/summary",
    response_model=AiSummaryResponse,
    summary="Resumo diário da SORA IA",
)
async def summary_endpoint(
    day: date | None = Query(default=None, alias="date"),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiSummaryResponse:
    return await ai_summary(
        session,
        tenant_id=principal.tenant_id,
        day=day,
    )


@router.get(
    "/birthday-credits",
    response_model=list[BirthdayCreditResponse],
    summary="Lista créditos de aniversário gerados",
)
async def birthday_credits_endpoint(
    year: str | None = Query(default=None),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[BirthdayCreditResponse]:
    return await list_birthday_credits(session, year=year)


@router.post(
    "/birthday-credits/run",
    response_model=BirthdayCreditRunResponse,
    summary="Gera créditos para aniversariantes dos próximos 7 dias",
)
async def run_birthday_credits_endpoint(
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> BirthdayCreditRunResponse:
    result = await create_birthday_credits(
        session,
        tenant_id=principal.tenant_id,
    )
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="ai.birthday_credits.run",
        resource_type="client_credit",
        resource_id=None,
        ip_address=client_ip(request),
        details={"created": result.created, "year": result.year},
    )
    return result


@router.get(
    "/conversations",
    response_model=list[AiConversationResponse],
    summary="Lista conversas da central",
)
async def conversations_endpoint(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AiConversationResponse]:
    return await list_conversations(session)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AiConversationDetailResponse,
    summary="Detalhe e histórico de uma conversa",
)
async def conversation_detail_endpoint(
    conversation_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiConversationDetailResponse:
    try:
        return await conversation_detail(session, conversation_id)
    except AiConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        ) from exc


@router.post(
    "/conversations/{conversation_id}/takeover",
    response_model=AiConversationDetailResponse,
    summary="Assume a conversa (atendimento humano)",
)
async def takeover_endpoint(
    conversation_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiConversationDetailResponse:
    try:
        result = await takeover_conversation(
            session,
            tenant_id=principal.tenant_id,
            conversation_id=conversation_id,
        )
    except AiConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="ai.conversation.takeover",
        resource_type="ai_conversation",
        resource_id=conversation_id,
        ip_address=client_ip(request),
    )
    return result


@router.post(
    "/conversations/{conversation_id}/approve",
    response_model=AiConversationDetailResponse,
    summary="Aprova uma exceção solicitada pelo cliente",
)
async def approve_endpoint(
    conversation_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiConversationDetailResponse:
    try:
        result = await approve_conversation(
            session,
            tenant_id=principal.tenant_id,
            conversation_id=conversation_id,
        )
    except AiConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        ) from exc
    except AiApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversa não está aguardando aprovação",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="ai.conversation.approve",
        resource_type="ai_conversation",
        resource_id=conversation_id,
        ip_address=client_ip(request),
    )
    return result


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AiMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envia resposta humana pela central",
)
async def human_message_endpoint(
    conversation_id: UUID,
    body: AiConversationReplyRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiMessageResponse:
    try:
        message = await send_human_message(
            session,
            tenant_id=principal.tenant_id,
            conversation_id=conversation_id,
            content=body.content,
        )
    except AiConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="ai.conversation.reply",
        resource_type="ai_conversation",
        resource_id=conversation_id,
        ip_address=client_ip(request),
    )
    return message


@router.post(
    "/conversations/{conversation_id}/close",
    response_model=AiConversationDetailResponse,
    summary="Encerra uma conversa",
)
async def close_endpoint(
    conversation_id: UUID,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AiConversationDetailResponse:
    try:
        result = await close_conversation(
            session,
            tenant_id=principal.tenant_id,
            conversation_id=conversation_id,
        )
    except AiConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="ai.conversation.close",
        resource_type="ai_conversation",
        resource_id=conversation_id,
        ip_address=client_ip(request),
    )
    return result
