"""SORA IA determinística: WhatsApp, guardrails e central de conversas."""

import calendar
import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.api.schemas.ai import (
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMessageResponse,
    AiSummaryResponse,
    BirthdayCreditResponse,
    BirthdayCreditRunResponse,
    BirthdayItemResponse,
    WhatsAppWebhookResponse,
)
from app.core.config import settings
from app.core.whatsapp import send_whatsapp_message
from app.db.rls import set_tenant_context
from app.models import (
    AiConversation,
    AiMessage,
    Appointment,
    AppointmentStatus,
    Client,
    ClientCredit,
    ConversationStatus,
    MessageDirection,
    Service,
    Tenant,
    TenantSettings,
)
from app.modules.agenda.public_service import (
    _client_by_phone,
    _tenant_id_by_slug,
    create_magic_link,
    normalize_phone,
)
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

INJECTION_MARKERS = (
    "ignore",
    "prompt",
    "system",
    "tenant",
    "outra clinica",
    "outro tenant",
    "todos os clientes",
    "score",
    "bloqueado",
    "sql",
)
BOOKING_MARKERS = ("agendar", "agenda", "horario", "horarios", "vaga", "marcar")
PRICE_MARKERS = ("preco", "valor", "valores", "quanto", "custa")
MY_APPOINTMENT_MARKERS = (
    "meus agendamentos",
    "minhas reservas",
    "meu horario",
    "meus horarios",
)
HUMAN_MARKERS = ("atendente", "humano", "falar com", "recepcao")
APPROVAL_MARKERS = (
    "excecao",
    "abrir mao",
    "sem cobrar",
    "doente",
    "encaixe",
    "desconto",
    "remarcar sem",
)
CANCELLATION_MARKERS = (
    "cancelamento",
    "cancelar",
    "atraso",
    "politica de",
    "regra de",
)
LOCATION_MARKERS = (
    "endereco",
    "onde fica",
    "estacionamento",
    "localizacao",
    "como chegar",
)
GREETING_MARKERS = ("oi", "ola", "bom dia", "boa tarde", "boa noite")
ZERO = Decimal("0.00")


class AiTenantNotFoundError(Exception):
    """Clínica inexistente/inativa."""


class AiConversationNotFoundError(Exception):
    """Conversa inexistente no tenant."""


class AiApprovalError(Exception):
    """Conversa não está aguardando aprovação."""


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _money(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _message_response(message: AiMessage) -> AiMessageResponse:
    return AiMessageResponse(
        id=message.id,
        direction=message.direction,
        content=message.content,
        intent=message.intent,
        created_at=message.created_at,
    )


async def _get_or_create_conversation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    phone: str,
    client: Client | None,
) -> AiConversation:
    conversation = await session.scalar(
        select(AiConversation)
        .where(
            AiConversation.phone == phone,
            AiConversation.status.in_(
                (ConversationStatus.OPEN, ConversationStatus.HUMAN)
            ),
        )
        .order_by(AiConversation.last_message_at.desc())
        .limit(1)
    )
    if conversation is None:
        conversation = AiConversation(
            tenant_id=tenant_id,
            client_id=client.id if client is not None else None,
            phone=phone,
            status=ConversationStatus.OPEN,
            last_message_at=datetime.now(UTC),
        )
        session.add(conversation)
        await session.flush()
    elif client is not None and conversation.client_id is None:
        conversation.client_id = client.id
    return conversation


def _add_message(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation: AiConversation,
    direction: MessageDirection,
    content: str,
    intent: str | None,
) -> AiMessage:
    message = AiMessage(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        direction=direction,
        content=content,
        intent=intent,
    )
    session.add(message)
    conversation.last_message_at = datetime.now(UTC)
    return message


async def _price_reply(session: AsyncSession) -> str:
    services = (
        await session.scalars(
            select(Service)
            .where(Service.is_active)
            .order_by(Service.name)
            .limit(10)
        )
    ).all()
    if not services:
        return "Ainda não há serviços cadastrados para consulta."
    lines = ["Nossos serviços:"]
    for service in services:
        price = (
            _money(service.price)
            if service.show_average_price
            else "sob consulta"
        )
        lines.append(f"• {service.name}: {price} ({service.duration_minutes} min)")
    return "\n".join(lines)


async def _appointment_reply(
    session: AsyncSession,
    *,
    client: Client | None,
) -> str:
    if client is None:
        return (
            "Não encontrei agendamentos para este número. "
            "Posso gerar um link para você agendar."
        )
    appointments = (
        await session.scalars(
            select(Appointment)
            .where(
                Appointment.client_id == client.id,
                Appointment.starts_at >= datetime.now(UTC),
                Appointment.status.notin_(
                    (
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.EXPIRED,
                    )
                ),
            )
            .order_by(Appointment.starts_at)
            .limit(5)
        )
    ).all()
    if not appointments:
        return "Você não tem agendamentos futuros."
    tz = ZoneInfo(settings.default_tenant_timezone)
    lines = ["Seus próximos agendamentos:"]
    for appointment in appointments:
        local = appointment.starts_at.astimezone(tz)
        lines.append(
            f"• {local:%d/%m às %H:%M} — {appointment.service.name}"
        )
    return "\n".join(lines)


async def handle_whatsapp_message(
    session: AsyncSession,
    redis: Redis,
    *,
    tenant_slug: str,
    phone: str,
    text: str,
) -> WhatsAppWebhookResponse:
    """Atende uma mensagem do roteador interno e grava o histórico."""
    tenant_id = await _tenant_id_by_slug(session, tenant_slug)
    if tenant_id is None:
        raise AiTenantNotFoundError
    await set_tenant_context(session, tenant_id)
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None or not tenant.is_active:
        raise AiTenantNotFoundError

    digits = normalize_phone(phone)
    client = await _client_by_phone(session, digits)
    conversation = await _get_or_create_conversation(
        session,
        tenant_id=tenant_id,
        phone=digits,
        client=client,
    )
    _add_message(
        session,
        tenant_id=tenant_id,
        conversation=conversation,
        direction=MessageDirection.INBOUND,
        content=text.strip(),
        intent=None,
    )

    tenant_settings = await session.get(TenantSettings, tenant_id)
    agent_name = (
        tenant_settings.agent_name if tenant_settings is not None else "Sora"
    )
    normalized = _normalize_text(text)
    intent = "fallback"

    if any(marker in normalized for marker in INJECTION_MARKERS):
        intent = "guardrail"
        reply = (
            "Posso ajudar com agendamentos, horários e valores dos serviços. "
            "Como posso ajudar?"
        )
    elif any(marker in normalized for marker in MY_APPOINTMENT_MARKERS):
        intent = "my_appointments"
        reply = await _appointment_reply(session, client=client)
    elif any(marker in normalized for marker in APPROVAL_MARKERS):
        intent = "approval"
        conversation.status = ConversationStatus.HUMAN
        conversation.needs_approval = True
        conversation.approval_note = text.strip()[:500]
        reply = (
            "Entendi. Vou pedir uma aprovação da equipe da clínica e "
            "retorno em seguida."
        )
    elif any(marker in normalized for marker in BOOKING_MARKERS):
        intent = "booking"
        if client is not None and client.is_blocked:
            reply = (
                "No momento não consigo concluir o agendamento. "
                "Fale com a recepção da clínica."
            )
        else:
            link = await create_magic_link(
                session,
                redis,
                slug=tenant_slug,
                phone=digits,
            )
            reply = (
                f"Claro! Escolha seu horário neste link seguro "
                f"(válido por 20 minutos): {link.url}"
            )
    elif any(marker in normalized for marker in PRICE_MARKERS):
        intent = "prices"
        reply = await _price_reply(session)
        if (
            tenant_settings is not None
            and tenant_settings.agent_upsell
        ):
            reply = f"{reply} {tenant_settings.agent_upsell.strip()}"
    elif any(marker in normalized for marker in CANCELLATION_MARKERS) and (
        tenant_settings is not None
        and tenant_settings.agent_cancellation_policy
    ):
        intent = "policy"
        reply = tenant_settings.agent_cancellation_policy.strip()
    elif any(marker in normalized for marker in LOCATION_MARKERS) and (
        tenant_settings is not None and tenant_settings.agent_address_info
    ):
        intent = "location"
        reply = tenant_settings.agent_address_info.strip()
    elif any(marker in normalized for marker in HUMAN_MARKERS):
        intent = "human"
        conversation.status = ConversationStatus.HUMAN
        reply = "Vou chamar a equipe da clínica para continuar seu atendimento."
    elif normalized in GREETING_MARKERS:
        intent = "greeting"
        if (
            tenant_settings is not None
            and tenant_settings.agent_welcome_message
        ):
            reply = tenant_settings.agent_welcome_message.strip()
        else:
            reply = (
                f"Olá! Sou a {agent_name}, atendente virtual da {tenant.name}. "
                "Posso ajudar com agendamento, horários ou valores."
            )
    else:
        reply = (
            f"Sou a {agent_name}. Posso ajudar com agendamento, horários e "
            "valores dos serviços. O que você precisa?"
        )

    _add_message(
        session,
        tenant_id=tenant_id,
        conversation=conversation,
        direction=MessageDirection.OUTBOUND,
        content=reply,
        intent=intent,
    )
    await session.commit()
    await send_whatsapp_message(phone=digits, text=reply)
    return WhatsAppWebhookResponse(
        conversation_id=conversation.id,
        reply=reply,
        intent=intent,
        status=conversation.status,
    )


async def list_conversations(
    session: AsyncSession,
) -> list[AiConversationResponse]:
    conversations = (
        await session.scalars(
            select(AiConversation)
            .order_by(AiConversation.last_message_at.desc())
            .limit(100)
        )
    ).all()
    if not conversations:
        return []
    ids = [conversation.id for conversation in conversations]
    rows = (
        await session.execute(
            select(
                AiMessage.conversation_id,
                AiMessage.content,
                AiMessage.intent,
            )
            .where(AiMessage.conversation_id.in_(ids))
            .order_by(AiMessage.created_at.desc())
        )
    ).all()
    previews: dict[UUID, str] = {}
    intents: dict[UUID, str] = {}
    for conversation_id, content, intent in rows:
        previews.setdefault(conversation_id, content)
        if intent is not None:
            intents.setdefault(conversation_id, intent)
    return [
        AiConversationResponse(
            id=conversation.id,
            client_id=conversation.client_id,
            client_name=(
                conversation.client.full_name
                if conversation.client is not None
                else None
            ),
            phone=conversation.phone,
            status=conversation.status,
            needs_approval=conversation.needs_approval,
            approval_note=conversation.approval_note,
            last_message=previews.get(conversation.id),
            last_message_at=conversation.last_message_at,
            last_intent=intents.get(conversation.id),
        )
        for conversation in conversations
    ]


async def _get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> AiConversation:
    conversation = await session.get(AiConversation, conversation_id)
    if conversation is None:
        raise AiConversationNotFoundError
    return conversation


async def conversation_detail(
    session: AsyncSession,
    conversation_id: UUID,
) -> AiConversationDetailResponse:
    conversation = await _get_conversation(session, conversation_id)
    messages = (
        await session.scalars(
            select(AiMessage)
            .where(AiMessage.conversation_id == conversation.id)
            .order_by(AiMessage.created_at)
        )
    ).all()
    last = messages[-1].content if messages else None
    return AiConversationDetailResponse(
        id=conversation.id,
        client_id=conversation.client_id,
        client_name=(
            conversation.client.full_name
            if conversation.client is not None
            else None
        ),
        phone=conversation.phone,
        status=conversation.status,
        needs_approval=conversation.needs_approval,
        approval_note=conversation.approval_note,
        last_message=last,
        last_message_at=conversation.last_message_at,
        messages=[_message_response(message) for message in messages],
    )


async def takeover_conversation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
) -> AiConversationDetailResponse:
    conversation = await _get_conversation(session, conversation_id)
    conversation.status = ConversationStatus.HUMAN
    _add_message(
        session,
        tenant_id=tenant_id,
        conversation=conversation,
        direction=MessageDirection.OUTBOUND,
        content="Atendimento assumido pela equipe da clínica.",
        intent="takeover",
    )
    await session.commit()
    await set_tenant_context(session, tenant_id)
    return await conversation_detail(session, conversation_id)


async def approve_conversation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
) -> AiConversationDetailResponse:
    """Aprova a exceção solicitada e devolve a conversa para a SORA IA."""
    conversation = await _get_conversation(session, conversation_id)
    if not conversation.needs_approval or (
        conversation.status == ConversationStatus.CLOSED
    ):
        raise AiApprovalError
    conversation.needs_approval = False
    conversation.approval_note = None
    conversation.status = ConversationStatus.OPEN
    content = (
        "A equipe da clínica aprovou a sua solicitação. "
        "Como posso ajudar agora?"
    )
    _add_message(
        session,
        tenant_id=tenant_id,
        conversation=conversation,
        direction=MessageDirection.OUTBOUND,
        content=content,
        intent="approval",
    )
    await session.commit()
    await send_whatsapp_message(phone=conversation.phone, text=content)
    await set_tenant_context(session, tenant_id)
    return await conversation_detail(session, conversation_id)


async def send_human_message(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
    content: str,
) -> AiMessageResponse:
    conversation = await _get_conversation(session, conversation_id)
    conversation.status = ConversationStatus.HUMAN
    message = _add_message(
        session,
        tenant_id=tenant_id,
        conversation=conversation,
        direction=MessageDirection.OUTBOUND,
        content=content.strip(),
        intent="human",
    )
    await session.commit()
    await send_whatsapp_message(
        phone=conversation.phone,
        text=content.strip(),
    )
    return _message_response(message)


async def close_conversation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
) -> AiConversationDetailResponse:
    conversation = await _get_conversation(session, conversation_id)
    conversation.status = ConversationStatus.CLOSED
    conversation.needs_approval = False
    conversation.approval_note = None
    await session.commit()
    await set_tenant_context(session, tenant_id)
    return await conversation_detail(session, conversation_id)


async def _birthdays(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    today: date,
) -> list[BirthdayItemResponse]:
    clients = (
        await session.scalars(
            select(Client).where(
                Client.tenant_id == tenant_id,
                Client.birth_date.is_not(None),
            )
        )
    ).all()
    items: list[BirthdayItemResponse] = []
    for client in clients:
        birth_date = client.birth_date
        if birth_date is None:
            continue
        year = today.year
        for offset in (0, 1):
            candidate_year = year + offset
            day = min(
                birth_date.day,
                calendar.monthrange(candidate_year, birth_date.month)[1],
            )
            candidate = date(candidate_year, birth_date.month, day)
            if candidate >= today:
                days_until = (candidate - today).days
                if days_until <= 7:
                    items.append(
                        BirthdayItemResponse(
                            client_id=client.id,
                            full_name=client.full_name,
                            birth_date=birth_date,
                            days_until=days_until,
                        )
                    )
                break
    return sorted(items, key=lambda item: item.days_until)


async def ai_summary(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    day: date | None = None,
) -> AiSummaryResponse:
    tz = ZoneInfo(settings.default_tenant_timezone)
    today = day or datetime.now(tz).date()
    start = datetime.combine(today, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(
        today + timedelta(days=1),
        time.min,
        tzinfo=tz,
    ).astimezone(UTC)

    open_count = await session.scalar(
        select(func.count(AiConversation.id)).where(
            AiConversation.status == ConversationStatus.OPEN
        )
    )
    human_count = await session.scalar(
        select(func.count(AiConversation.id)).where(
            AiConversation.status == ConversationStatus.HUMAN
        )
    )
    approval_count = await session.scalar(
        select(func.count(AiConversation.id)).where(
            AiConversation.needs_approval.is_(True),
            AiConversation.status != ConversationStatus.CLOSED,
        )
    )
    messages_today = await session.scalar(
        select(func.count(AiMessage.id)).where(
            AiMessage.created_at >= start,
            AiMessage.created_at < end,
        )
    )
    appointments_today = await session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
            Appointment.status.notin_(
                (AppointmentStatus.CANCELLED, AppointmentStatus.EXPIRED)
            ),
        )
    )
    tenant_settings = await session.get(TenantSettings, tenant_id)
    return AiSummaryResponse(
        date=today,
        agent_name=(
            tenant_settings.agent_name
            if tenant_settings is not None
            else "Sora"
        ),
        open_conversations=int(open_count or 0),
        human_conversations=int(human_count or 0),
        approvals_pending=int(approval_count or 0),
        messages_today=int(messages_today or 0),
        appointments_today=int(appointments_today or 0),
        birthdays=await _birthdays(session, tenant_id=tenant_id, today=today),
    )


def _credit_response(credit: ClientCredit) -> BirthdayCreditResponse:
    return BirthdayCreditResponse(
        id=credit.id,
        client_id=credit.client_id,
        client_name=credit.client.full_name,
        amount=credit.amount,
        used_amount=credit.used_amount,
        reason=credit.reason,
        reference=credit.reference,
        expires_at=credit.expires_at,
    )


async def create_birthday_credits(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    today: date | None = None,
) -> BirthdayCreditRunResponse:
    """Gera créditos idempotentes para aniversariantes dos próximos 7 dias."""
    current = today or datetime.now(
        ZoneInfo(settings.default_tenant_timezone)
    ).date()
    reference = str(current.year)
    tenant_settings = await session.get(TenantSettings, tenant_id)
    amount = (
        tenant_settings.birthday_credit_amount
        if tenant_settings is not None
        else ZERO
    )
    if amount <= 0:
        return BirthdayCreditRunResponse(
            year=reference,
            created=0,
            total_amount=ZERO,
            credits=[],
        )

    items = await _birthdays(session, tenant_id=tenant_id, today=current)
    created: list[ClientCredit] = []
    notifications: list[tuple[str, str]] = []
    for item in items:
        existing = await session.scalar(
            select(ClientCredit).where(
                ClientCredit.client_id == item.client_id,
                ClientCredit.reason == "BIRTHDAY",
                ClientCredit.reference == reference,
            )
        )
        if existing is not None:
            continue
        client = await session.get(Client, item.client_id)
        if client is None:
            continue
        credit = ClientCredit(
            tenant_id=tenant_id,
            client_id=client.id,
            amount=amount,
            used_amount=ZERO,
            reason="BIRTHDAY",
            reference=reference,
            expires_at=current + timedelta(days=30),
            client=client,
        )
        session.add(credit)
        created.append(credit)
        notifications.append(
            (
                client.phone,
                f"Feliz aniversário, {client.full_name}! "
                f"Você ganhou {_money(amount)} de crédito na clínica, "
                "válido por 30 dias.",
            )
        )
    await session.commit()
    for phone, message in notifications:
        await send_whatsapp_message(phone=phone, text=message)
    return BirthdayCreditRunResponse(
        year=reference,
        created=len(created),
        total_amount=(amount * len(created)).quantize(Decimal("0.01")),
        credits=[_credit_response(credit) for credit in created],
    )


async def list_birthday_credits(
    session: AsyncSession,
    *,
    year: str | None = None,
) -> list[BirthdayCreditResponse]:
    query = select(ClientCredit).where(ClientCredit.reason == "BIRTHDAY")
    if year:
        query = query.where(ClientCredit.reference == year)
    credits = (
        await session.scalars(query.order_by(ClientCredit.created_at.desc()))
    ).all()
    return [_credit_response(credit) for credit in credits]

