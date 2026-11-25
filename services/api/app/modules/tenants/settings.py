"""Configurações de sinal/score, tema e agente do tenant."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tenants import TenantSettingsResponse
from app.db.rls import set_tenant_context
from app.models import TenantSettings

DEFAULT_THEME_COLOR = "#4f46e5"
DEFAULT_AGENT_NAME = "Sora"


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

    await session.commit()
    # O commit encerra o SET LOCAL do RLS; reaplica para a resposta.
    await set_tenant_context(session, tenant_id)
    return settings_response(settings)
