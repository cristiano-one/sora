"""Configuração centralizada de logging (sem PII, tokens ou senhas)."""

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Configura o logging da aplicação com o nível definido nas settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
