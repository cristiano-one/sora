"""Configurações de sinal/score, tema e agente do tenant."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tenants import TenantSettingsResponse
from app.core.crypto import encrypt_text
from app.db.rls import set_tenant_context
from app.models import TenantSettings

DEFAULT_THEME_COLOR = "#4f46e5"
DEFAULT_AGENT_NAME = "Sora"
DEFAULT_AI_PROVIDER = "mock"
DEFAULT_AI_MODEL = "llama-3.3-70b-versatile"


class TenantSettingsValidationError(Exception):
    """Combinação inválida de limite de score e valor de sinal."""


async def get_tenant_settings(
    session: AsyncSession,
    tenant_id: UUID,
) -> TenantSettings | None:
    return await session.get(TenantSettings, tenant_id)


def settings_response(
    settings: TenantSettings | None,
) -> TenantSettingsResponse:
    return TenantSettingsResponse(
        deposit_score_threshold=(
            settings.deposit_score_threshold if settings is not None else None
        ),
        deposit_amount_low_score=(
            settings.deposit_amount_low_score if settings is not None else None
        ),
        theme_primary_color=(
            settings.theme_primary_color
            if settings is not None
            else DEFAULT_THEME_COLOR
        ),
        agent_name=(
            settings.agent_name if settings is not None else DEFAULT_AGENT_NAME
        ),
        agent_tone=(
            settings.agent_tone if settings is not None else "acolhedor"
        ),
        agent_welcome_message=(
            settings.agent_welcome_message if settings is not None else None
        ),
        agent_knowledge=(
            settings.agent_knowledge if settings is not None else None
        ),
        agent_cancellation_policy=(
            settings.agent_cancellation_policy
            if settings is not None
            else None
        ),
        agent_address_info=(
            settings.agent_address_info if settings is not None else None
        ),
        agent_upsell=settings.agent_upsell if settings is not None else None,
        ai_provider=(
            settings.ai_provider
            if settings is not None
            else DEFAULT_AI_PROVIDER
        ),
        ai_model=(
            settings.ai_model if settings is not None else DEFAULT_AI_MODEL
        ),
        ai_key_configured=(
            settings is not None
            and settings.ai_api_key_encrypted is not None
        ),
        fiscal_enabled=(
            settings.fiscal_enabled if settings is not None else False
        ),
        fiscal_provider=(
            settings.fiscal_provider if settings is not None else "mock"
        ),
        fiscal_municipality=(
            settings.fiscal_municipality if settings is not None else None
        ),
        fiscal_service_code=(
            settings.fiscal_service_code if settings is not None else None
        ),
        fiscal_email=(
            settings.fiscal_email if settings is not None else None
        ),
        enable_tithe_and_offering=(
            settings.enable_tithe_and_offering
            if settings is not None
            else False
        ),
        tithe_percentage=(
            settings.tithe_percentage if settings is not None else Decimal("10.00")
        ),
        offering_amount=(
            settings.offering_amount if settings is not None else Decimal("0.00")
        ),
        birthday_credit_amount=(
            settings.birthday_credit_amount
            if settings is not None
            else Decimal("0.00")
        ),
    )


async def get_tenant_settings_response(
    session: AsyncSession,
    tenant_id: UUID,
) -> TenantSettingsResponse:
    return settings_response(await get_tenant_settings(session, tenant_id))


async def update_tenant_settings(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    changes: dict[str, object],
) -> TenantSettingsResponse:
    settings = await get_tenant_settings(session, tenant_id)
    if settings is None:
        settings = TenantSettings(tenant_id=tenant_id)
        session.add(settings)

    changes = dict(changes)
    ai_key = changes.pop("ai_api_key", None)
    clear_ai_key = bool(changes.pop("clear_ai_api_key", False))
    if ai_key is not None and clear_ai_key:
        raise TenantSettingsValidationError(
            "Envie a nova chave ou solicite a remoção, não ambos."
        )
    new_key = settings.ai_api_key_encrypted
    if ai_key is not None:
        key_text = str(ai_key).strip()
        if not key_text:
            raise TenantSettingsValidationError("Chave da Groq vazia.")
        new_key = encrypt_text(key_text)
    if clear_ai_key:
        new_key = None
    target_provider = str(
        changes.get("ai_provider")
        or settings.ai_provider
        or DEFAULT_AI_PROVIDER
    )
    if target_provider not in {"mock", "groq"}:
        raise TenantSettingsValidationError("Provedor de IA inválido.")
    if target_provider == "groq" and not new_key:
        raise TenantSettingsValidationError(
            "Informe a chave da Groq para usar esse provedor."
        )
    target_model = str(
        changes.get("ai_model")
        or settings.ai_model
        or DEFAULT_AI_MODEL
    ).strip()
    if not target_model:
        raise TenantSettingsValidationError("Modelo de IA inválido.")

    settings.ai_provider = target_provider
    settings.ai_model = target_model
    settings.ai_api_key_encrypted = new_key

    threshold = changes.get(
        "deposit_score_threshold",
        settings.deposit_score_threshold,
    )
    amount = changes.get(
        "deposit_amount_low_score",
        settings.deposit_amount_low_score,
    )
    if threshold is not None and (
        amount is None or Decimal(str(amount)) <= 0
    ):
        raise TenantSettingsValidationError(
            "deposit_amount_low_score deve ser positivo quando "
            "deposit_score_threshold está definido"
        )

    if "deposit_score_threshold" in changes:
        settings.deposit_score_threshold = (
            int(str(threshold)) if threshold is not None else None
        )
    if "deposit_amount_low_score" in changes:
        settings.deposit_amount_low_score = (
            Decimal(str(amount)) if amount is not None else None
        )
    if "theme_primary_color" in changes:
        settings.theme_primary_color = str(changes["theme_primary_color"])
    if "agent_name" in changes:
        settings.agent_name = str(changes["agent_name"])
    for field in (
        "agent_tone",
        "agent_welcome_message",
        "agent_knowledge",
        "agent_cancellation_policy",
        "agent_address_info",
        "agent_upsell",
        "fiscal_provider",
        "fiscal_municipality",
        "fiscal_service_code",
        "fiscal_email",
    ):
        if field in changes:
            value = changes[field]
            setattr(
                settings,
                field,
                str(value).strip() if value is not None else None,
            )
    if changes.get("fiscal_enabled") is not None:
        settings.fiscal_enabled = bool(changes["fiscal_enabled"])
    if changes.get("enable_tithe_and_offering") is not None:
        settings.enable_tithe_and_offering = bool(
            changes["enable_tithe_and_offering"]
        )
    if changes.get("tithe_percentage") is not None:
        settings.tithe_percentage = Decimal(str(changes["tithe_percentage"]))
    if changes.get("offering_amount") is not None:
        settings.offering_amount = Decimal(str(changes["offering_amount"]))
    if changes.get("birthday_credit_amount") is not None:
        settings.birthday_credit_amount = Decimal(
            str(changes["birthday_credit_amount"])
        )

    await session.commit()
    # O commit encerra o SET LOCAL do RLS; reaplica para a resposta.
    await set_tenant_context(session, tenant_id)
    return settings_response(settings)
