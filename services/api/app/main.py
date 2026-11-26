"""Ponto de entrada da aplicação FastAPI da Sora Studio."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.agenda import router as agenda_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.automations import router as automations_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.clients import router as clients_router
from app.api.routes.finance import router as finance_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.payments import router as payments_router
from app.api.routes.payroll import router as payroll_router
from app.api.routes.public_booking import router as public_booking_router
from app.api.routes.sales import router as sales_router
from app.api.routes.storage import router as storage_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.system import router as system_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes.users import router as users_router
from app.api.routes.whatsapp import router as whatsapp_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import create_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cria e encerra o cliente Redis junto com a aplicação."""
    redis = create_redis(settings.redis_url)
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()


def create_app() -> FastAPI:
    """Cria e configura a instância da aplicação FastAPI."""
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # Health check fica na raiz (probes de orquestradores/edge).
    application.include_router(health_router)

    # Rotas de negócio versionadas.
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(tenants_router, prefix=settings.api_v1_prefix)
    application.include_router(system_router, prefix=settings.api_v1_prefix)
    application.include_router(users_router, prefix=settings.api_v1_prefix)
    application.include_router(catalog_router, prefix=settings.api_v1_prefix)
    application.include_router(clients_router, prefix=settings.api_v1_prefix)
    application.include_router(payments_router, prefix=settings.api_v1_prefix)
    application.include_router(storage_router, prefix=settings.api_v1_prefix)
    application.include_router(finance_router, prefix=settings.api_v1_prefix)
    application.include_router(sales_router, prefix=settings.api_v1_prefix)
    application.include_router(payroll_router, prefix=settings.api_v1_prefix)
    application.include_router(inventory_router, prefix=settings.api_v1_prefix)
    application.include_router(ai_router, prefix=settings.api_v1_prefix)
    application.include_router(whatsapp_router, prefix=settings.api_v1_prefix)
    application.include_router(
        automations_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(agenda_router, prefix=settings.api_v1_prefix)
    application.include_router(
        subscriptions_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(
        public_booking_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_app()
