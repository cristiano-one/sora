"""Motor de automações de relacionamento (WhatsApp)."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.whatsapp import send_whatsapp_message
from app.db.rls import set_tenant_context
from app.models import (
    Appointment,
    AppointmentStatus,
    AutomationRule,
    AutomationRun,
    AutomationRunStatus,
    AutomationTrigger,
    Client,
)
from app.modules.whatsapp.service import get_credentials_for_tenant
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_RULES: list[dict[str, object]] = [
    {
        "trigger": AutomationTrigger.BOOKING_CONFIRMATION,
        "name": "Confirmação de agendamento",
        "delay_minutes": 0,
        "template": (
            "Oi {first_name}! Seu horário de {service} foi reservado para "
            "{date} às {time}. Até lá!"
        ),
    },
    {
        "trigger": AutomationTrigger.REMINDER_24H,
        "name": "Lembrete 24h",
        "delay_minutes": -24 * 60,
        "template": (
            "Lembrete: {first_name}, amanhã às {time} você tem {service} "
            "com {collaborator}. Podemos confirmar?"
        ),
    },
    {
        "trigger": AutomationTrigger.REMINDER_2H,
        "name": "Lembrete 2h",
        "delay_minutes": -2 * 60,
        "template": (
            "{first_name}, seu atendimento de {service} é hoje às {time}. "
            "Te esperamos!"
        ),
    },
    {
        "trigger": AutomationTrigger.POST_SERVICE,
        "name": "Pós-atendimento",
        "delay_minutes": 24 * 60,
        "template": (
            "Oi {first_name}! Como foi seu atendimento de {service}? "
            "Sua opinião ajuda a cuidarmos cada vez melhor."
        ),
    },
    {
        "trigger": AutomationTrigger.WINBACK_60D,
        "name": "Recuperação 60 dias",
        "delay_minutes": 0,
        "template": (
            "Sentimos sua falta, {first_name}! Que tal marcar um novo "
            "atendimento? Estamos à disposição."
        ),
    },
    {
        "trigger": AutomationTrigger.BIRTHDAY,
        "name": "Aniversário",
        "delay_minutes": 0,
        "template": (
            "Feliz aniversário, {first_name}! Preparamos um carinho especial "
            "para você."
        ),
    },
]


class AutomationNotFoundError(Exception):
    """Régua/execução inexistente."""


async def ensure_default_rules(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[AutomationRule]:
    existing = list(
        (
            await session.scalars(
                select(AutomationRule).where(
                    AutomationRule.tenant_id == tenant_id
                )
            )
        ).all()
    )
    known = {rule.trigger for rule in existing}
    for item in DEFAULT_RULES:
        trigger = item["trigger"]
        if not isinstance(trigger, AutomationTrigger):
            continue
        if trigger in known:
            continue
        rule = AutomationRule(
            id=uuid4(),
            tenant_id=tenant_id,
            trigger=trigger,
            name=str(item["name"]),
            delay_minutes=(
                item["delay_minutes"]
                if isinstance(item["delay_minutes"], int)
                else 0
            ),
            template=str(item["template"]),
            is_active=True,
        )
        session.add(rule)
        existing.append(rule)
    if len(existing) > len(known):
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        await set_tenant_context(session, tenant_id)
    return list(existing)


async def list_rules(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[AutomationRule]:
    await ensure_default_rules(session, tenant_id=tenant_id)
    return list(
        (
            await session.scalars(
                select(AutomationRule)
                .where(AutomationRule.tenant_id == tenant_id)
                .order_by(AutomationRule.trigger)
            )
        ).all()
    )


async def get_rule(session: AsyncSession, rule_id: UUID) -> AutomationRule:
    rule = await session.get(AutomationRule, rule_id)
    if rule is None:
        raise AutomationNotFoundError
    return rule


async def update_rule(
    session: AsyncSession,
    *,
    rule: AutomationRule,
    changes: dict[str, object],
) -> AutomationRule:
    for field in ("name", "template", "is_active"):
        if field in changes and changes[field] is not None:
            setattr(rule, field, changes[field])
    await session.commit()
    await set_tenant_context(session, rule.tenant_id)
    return rule


async def _add_run(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    rule: AutomationRule,
    client_id: UUID,
    appointment_id: UUID | None,
    scheduled_for: datetime,
    dedupe_key: str,
) -> None:
    exists = await session.scalar(
        select(AutomationRun.id).where(
            AutomationRun.tenant_id == tenant_id,
            AutomationRun.dedupe_key == dedupe_key,
        )
    )
    if exists is not None:
        return
    session.add(
        AutomationRun(
            id=uuid4(),
            tenant_id=tenant_id,
            rule_id=rule.id,
            client_id=client_id,
            appointment_id=appointment_id,
            status=AutomationRunStatus.PENDING,
            scheduled_for=scheduled_for,
            dedupe_key=dedupe_key,
        )
    )


async def schedule_appointment_automations(
    session: AsyncSession,
    *,
    appointment: Appointment,
) -> None:
    rules = await ensure_default_rules(
        session,
        tenant_id=appointment.tenant_id,
    )
    now = datetime.now(UTC)
    by_trigger = {
        rule.trigger: rule for rule in rules if rule.is_active
    }
    for trigger in (
        AutomationTrigger.BOOKING_CONFIRMATION,
        AutomationTrigger.REMINDER_24H,
        AutomationTrigger.REMINDER_2H,
    ):
        rule = by_trigger.get(trigger)
        if rule is None:
            continue
        scheduled = now if trigger == AutomationTrigger.BOOKING_CONFIRMATION else (
            appointment.starts_at + timedelta(minutes=rule.delay_minutes)
        )
        if scheduled <= now and trigger != AutomationTrigger.BOOKING_CONFIRMATION:
            continue
        await _add_run(
            session,
            tenant_id=appointment.tenant_id,
            rule=rule,
            client_id=appointment.client_id,
            appointment_id=appointment.id,
            scheduled_for=scheduled,
            dedupe_key=f"{trigger.value}:{appointment.id}",
        )
    await session.commit()
    await set_tenant_context(session, appointment.tenant_id)


async def schedule_post_service(
    session: AsyncSession,
    *,
    appointment: Appointment,
) -> None:
    rules = await ensure_default_rules(
        session,
        tenant_id=appointment.tenant_id,
    )
    rule = next(
        (
            item
            for item in rules
            if item.trigger == AutomationTrigger.POST_SERVICE
            and item.is_active
        ),
        None,
    )
    if rule is None:
        return
    scheduled = datetime.now(UTC) + timedelta(minutes=rule.delay_minutes)
    await _add_run(
        session,
        tenant_id=appointment.tenant_id,
        rule=rule,
        client_id=appointment.client_id,
        appointment_id=appointment.id,
        scheduled_for=scheduled,
        dedupe_key=f"{AutomationTrigger.POST_SERVICE.value}:{appointment.id}",
    )
    await session.commit()
    await set_tenant_context(session, appointment.tenant_id)


async def skip_pending_for_appointment(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    appointment_id: UUID,
) -> None:
    runs = (
        await session.scalars(
            select(AutomationRun).where(
                AutomationRun.appointment_id == appointment_id,
                AutomationRun.status == AutomationRunStatus.PENDING,
            )
        )
    ).all()
    for run in runs:
        run.status = AutomationRunStatus.SKIPPED
        run.error = "Agendamento cancelado/expirado"
    await session.commit()
    await set_tenant_context(session, tenant_id)


async def schedule_winback_runs(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    today: date,
) -> int:
    rules = await ensure_default_rules(session, tenant_id=tenant_id)
    rule = next(
        (
            item
            for item in rules
            if item.trigger == AutomationTrigger.WINBACK_60D
            and item.is_active
        ),
        None,
    )
    if rule is None:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=60)
    last_appointment = (
        select(
            Appointment.client_id.label("client_id"),
            func.max(Appointment.starts_at).label("last_at"),
        )
        .where(Appointment.status == AppointmentStatus.COMPLETED)
        .group_by(Appointment.client_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Client.id, last_appointment.c.last_at)
            .join(last_appointment, last_appointment.c.client_id == Client.id)
            .where(last_appointment.c.last_at < cutoff)
        )
    ).all()
    bucket = today.toordinal() // 60
    created = 0
    for client_id, _last_at in rows:
        key = f"{AutomationTrigger.WINBACK_60D.value}:{client_id}:{bucket}"
        exists = await session.scalar(
            select(AutomationRun.id).where(
                AutomationRun.tenant_id == tenant_id,
                AutomationRun.dedupe_key == key,
            )
        )
        if exists is not None:
            continue
        session.add(
            AutomationRun(
                id=uuid4(),
                tenant_id=tenant_id,
                rule_id=rule.id,
                client_id=client_id,
                appointment_id=None,
                status=AutomationRunStatus.PENDING,
                scheduled_for=datetime.now(UTC),
                dedupe_key=key,
            )
        )
        created += 1
    if created:
        await session.commit()
        await set_tenant_context(session, tenant_id)
    return created


def _render(
    template: str,
    *,
    client: Client,
    appointment: Appointment | None,
) -> str:
    tz = ZoneInfo(settings.default_tenant_timezone)
    values = {
        "client_name": client.full_name,
        "first_name": client.full_name.split(" ")[0],
        "phone": client.phone,
        "service": appointment.service.name if appointment else "atendimento",
        "collaborator": (
            appointment.collaborator.full_name if appointment else "equipe"
        ),
        "date": (
            appointment.starts_at.astimezone(tz).strftime("%d/%m/%Y")
            if appointment
            else ""
        ),
        "time": (
            appointment.starts_at.astimezone(tz).strftime("%H:%M")
            if appointment
            else ""
        ),
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


async def run_due(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    now: datetime | None = None,
    limit: int = 50,
) -> dict[str, int]:
    moment = now or datetime.now(UTC)
    credentials = await get_credentials_for_tenant(session, tenant_id)
    runs = (
        await session.scalars(
            select(AutomationRun)
            .join(AutomationRule, AutomationRule.id == AutomationRun.rule_id)
            .where(
                AutomationRun.status == AutomationRunStatus.PENDING,
                AutomationRun.scheduled_for <= moment,
                AutomationRule.is_active.is_(True),
            )
            .order_by(AutomationRun.scheduled_for)
            .limit(limit)
        )
    ).all()
    sent = failed = skipped = 0
    for run in runs:
        rule = await session.get(AutomationRule, run.rule_id)
        client = await session.get(Client, run.client_id)
        if rule is None or client is None:
            run.status = AutomationRunStatus.SKIPPED
            run.error = "Régua ou cliente removido"
            skipped += 1
            continue
        appointment = (
            await session.get(Appointment, run.appointment_id)
            if run.appointment_id is not None
            else None
        )
        if appointment is not None and appointment.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.EXPIRED,
            AppointmentStatus.NO_SHOW,
        ):
            run.status = AutomationRunStatus.SKIPPED
            run.error = "Agendamento sem atendimento"
            skipped += 1
            continue
        text = _render(rule.template, client=client, appointment=appointment)
        if await send_whatsapp_message(
            phone=client.phone,
            text=text,
            credentials=credentials,
        ):
            run.status = AutomationRunStatus.SENT
            run.sent_at = moment
            sent += 1
        else:
            run.status = AutomationRunStatus.FAILED
            run.error = "Falha no envio WhatsApp"
            failed += 1
    await session.commit()
    await set_tenant_context(session, tenant_id)
    return {"processed": len(runs), "sent": sent, "failed": failed, "skipped": skipped}


async def list_runs(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[AutomationRun]:
    return list(
        (
            await session.scalars(
                select(AutomationRun)
                .order_by(AutomationRun.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
