"""Contexto de tenant aplicado às políticas de Row-Level Security (RLS)."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TENANT_CONTEXT_SETTING = "app.current_tenant_id"


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Define o tenant da transação atual de forma parametrizada (SET LOCAL).

    Usa ``set_config(..., true)`` porque ``SET LOCAL`` não aceita bind
    parameters. O valor é local à transação e não vaza para outras conexões
    do pool.
    """
    await session.execute(
        text("SELECT set_config(:setting, :tenant_id, true)"),
        {"setting": TENANT_CONTEXT_SETTING, "tenant_id": str(tenant_id)},
    )
