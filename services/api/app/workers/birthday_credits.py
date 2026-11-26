"""Worker de créditos de aniversário (executar via cron/scheduler)."""

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.db.rls import set_tenant_context
from app.db.session import create_engine, create_session_factory
from app.models import Tenant
from app.modules.ai.service import create_birthday_credits
from sqlalchemy import select

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BirthdayRunResult:
    tenants: int
    created: int
    errors: int


async def run_all() -> BirthdayRunResult:
    """Percorre tenants ativos e gera créditos idempotentes do ano."""
    owner_engine = create_engine(settings.migration_database_url)
    app_engine = create_engine(settings.database_url)
    owner_factory = create_session_factory(owner_engine)
    app_factory = create_session_factory(app_engine)
    created = 0
    errors = 0
    tenants_count = 0
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
                    result = await create_birthday_credits(
                        session,
                        tenant_id=tenant.id,
                    )
                    created += result.created
                    logger.info(
                        "birthday credits tenant=%s created=%s",
                        tenant.slug,
                        result.created,
                    )
                except Exception:
                    errors += 1
                    logger.exception(
                        "falha ao gerar créditos de aniversário tenant=%s",
                        tenant.slug,
                    )
    finally:
        await owner_engine.dispose()
        await app_engine.dispose()
    return BirthdayRunResult(
        tenants=tenants_count,
        created=created,
        errors=errors,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_all())
    logger.info(
        "birthday worker finalizado tenants=%s created=%s errors=%s",
        result.tenants,
        result.created,
        result.errors,
    )
    if result.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
