"""Configurações centralizadas da API (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# `config.py` está em services/api/app/core/config.py.
BASE_DIR = Path(__file__).resolve().parents[2]  # services/api
REPO_ROOT = BASE_DIR.parents[1]  # raiz do monorepo (sora/)

# Considera apenas arquivos .env que existem (dev local pode não ter copiado o .env).
_ENV_FILES = tuple(p for p in (REPO_ROOT / ".env", BASE_DIR / ".env") if p.exists())


class Settings(BaseSettings):
    """Configurações carregadas do ambiente e, opcionalmente, do arquivo `.env`."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Aplicação
    app_name: str = "Sora Studio API"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "DEBUG"
    api_v1_prefix: str = "/api/v1"

    # Infraestrutura (portas do HOST do compose de dev; ver .env.example)
    database_url: str = "postgresql+asyncpg://sora_app:sora_app_dev_only@127.0.0.1:5433/sora"
    migration_database_url: str = "postgresql+asyncpg://sora:sora_dev_only@127.0.0.1:5433/sora"
    redis_url: str = "redis://:sora_dev_only@127.0.0.1:6380/0"

    # Segurança / Autenticação
    jwt_secret_key: str = "change-me-in-production-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "sora-api"
    jwt_audience: str = "sora-clients"
    encryption_key: str = "change-me-encryption-key"


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única (cacheada) das configurações."""
    return Settings()


settings = get_settings()
