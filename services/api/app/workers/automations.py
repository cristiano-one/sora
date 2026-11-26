"""Worker de automações: recuperação e execução de mensagens vencidas."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.db.rls import set_tenant_context
from app.db.session import create_engine, create_session_factory
from app.models import Tenant
from app.modules.automations.service import (
    list_rules,
    run_due,
    schedule_winback_runs,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutomationRunResult:
    tenants: int
    processed: int
    sent: int
    failed: int
    skipped: int
    errors: int


async def run_all() -> AutomationRunResult:
    """Percorre tenants ativos, agenda recuperação e envia mensagens vencidas."""
    owner_engine = create_engine(settings.migration_database_url)
    app_engine = create_engine(settings.database_url)
    owner_factory = create_session_factory(owner_engine)
    app_factory = create_session_factory(app_engine)
    processed = sent = failed = skipped = errors = 0
    tenants_count = 0
    today = datetime.now(
        ZoneInfo(settings.default_tenant_timezone)
    ).date()
    try:
        async with owner_factory() as owner_session:
            tenants = (
                await owner_session.scalars(
                    select(Tenant)
                    .where(Tenant.is_active)
                    .order_by(Tenant.slug)
                )
            ).all()
            tenants_count = len(tenants)

        async with app_factory() as session:
            for tenant in tenants:
                try:
                    await set_tenant_context(session, tenant.id)
                    await list_rules(session, tenant_id=tenant.id)
                    await schedule_winback_runs(
                        session,
                        tenant_id=tenant.id,
                        today=today,
                    )
                    result = await run_due(
                        session,
                        tenant_id=tenant.id,
                    )
                    processed += result["processed"]
                    sent += result["sent"]
                    failed += result["failed"]
                    skipped += result["skipped"]
                    logger.info(
                        "automations tenant=%s processed=%s sent=%s",
                        tenant.slug,
                        result["processed"],
                        result["sent"],
                    )
                except Exception:
                    errors += 1
                    logger.exception(
                        "falha nas automações tenant=%s",
                        tenant.slug,
                    )
    finally:
        await owner_engine.dispose()
        await app_engine.dispose()
    return AutomationRunResult(
        tenants=tenants_count,
        processed=processed,
        sent=sent,
        failed=failed,
        skipped=skipped,
        errors=errors,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_all())
    logger.info(
        "automation worker tenants=%s processed=%s sent=%s failed=%s errors=%s",
        result.tenants,
        result.processed,
        result.sent,
        result.failed,
        result.errors,
    )
    if result.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
