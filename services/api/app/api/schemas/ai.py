"""Contratos da SORA IA e da central de conversas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import ConversationStatus, MessageDirection


class WhatsAppWebhookRequest(BaseModel):
    """Mensagem recebida do roteador interno do WhatsApp."""

    tenant_slug: str = Field(min_length=3, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    text: str = Field(min_length=1, max_length=2000)


class WhatsAppSimulationRequest(BaseModel):
    """Mensagem enviada pelo simulador autenticado da central."""

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
    needs_approval: bool
    approval_note: str | None
    last_message: str | None
    last_message_at: datetime
    last_intent: str | None = None


class AiConversationDetailResponse(AiConversationResponse):
    """Conversa com o histórico completo."""

    messages: list[AiMessageResponse]


class AiConversationReplyRequest(BaseModel):
    """Resposta humana enviada pela central."""

    content: str = Field(min_length=1, max_length=2000)


class AiProviderTestResponse(BaseModel):
    """Resultado do teste de conexão com o provedor de IA."""

    ok: bool
    provider: str
    model: str
    latency_ms: int
    reply: str


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
    approvals_pending: int
    messages_today: int
    appointments_today: int
    birthdays: list[BirthdayItemResponse]


class AiCheckinResponse(BaseModel):
    """Cliente que fez check-in e está na recepção."""

    appointment_id: UUID
    client_name: str
    service_name: str
    collaborator_name: str
    starts_at: datetime
    checked_in_at: datetime


class BirthdayCreditResponse(BaseModel):
    """Crédito de aniversário de um cliente."""

    id: UUID
    client_id: UUID
    client_name: str
    amount: Decimal
    used_amount: Decimal
    reason: str
    reference: str
    expires_at: date


class BirthdayCreditRunResponse(BaseModel):
    """Resultado da geração idempotente de créditos."""

    year: str
    created: int
    total_amount: Decimal
    credits: list[BirthdayCreditResponse]
