"""Ponto de entrada da aplicação FastAPI da Sora Studio."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Cria e configura a instância da aplicação FastAPI."""
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
    )

    # Health check fica na raiz (probes de orquestradores/edge).
    application.include_router(health_router)

    # Rotas de negócio futuras serão versionadas sob `settings.api_v1_prefix`.
    return application


app = create_app()
