"""Contratos da SORA IA e da central de conversas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import ConversationStatus, MessageDirection


class WhatsAppWebhookRequest(BaseModel):
    """Mensagem recebida do roteador interno do WhatsApp."""

    tenant_slug: str = Field(min_length=3, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    text: str = Field(min_length=1, max_length=2000)


class WhatsAppWebhookResponse(BaseModel):
    """Resposta automática gravada na conversa."""

    conversation_id: UUID
    reply: str
    intent: str
    status: ConversationStatus


class AiMessageResponse(BaseModel):
    """Mensagem de uma conversa."""

    id: UUID
    direction: MessageDirection
    content: str
    intent: str | None
    created_at: datetime


class AiConversationResponse(BaseModel):
    """Resumo de conversa para a central."""

    id: UUID
    client_id: UUID | None
    client_name: str | None
    phone: str
    status: ConversationStatus
    last_message: str | None
    last_message_at: datetime


class AiConversationDetailResponse(AiConversationResponse):
    """Conversa com o histórico completo."""

    messages: list[AiMessageResponse]


class AiConversationReplyRequest(BaseModel):
    """Resposta humana enviada pela central."""

    content: str = Field(min_length=1, max_length=2000)


class BirthdayItemResponse(BaseModel):
    """Aniversariante dos próximos dias."""

    client_id: UUID
    full_name: str
    birth_date: date
    days_until: int


class AiSummaryResponse(BaseModel):
    """Resumo diário da SORA IA."""

    date: date
    agent_name: str
    open_conversations: int
    human_conversations: int
    messages_today: int
    appointments_today: int
    birthdays: list[BirthdayItemResponse]
