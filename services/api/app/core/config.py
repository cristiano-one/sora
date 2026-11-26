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
    default_tenant_timezone: str = "America/Sao_Paulo"
    public_booking_base_url: str = "http://localhost:3000"
    internal_api_token: str = "dev-internal-token"
    payment_provider: str = "mock"
    payment_pix_key: str = "pix@sora.local"
    payment_merchant_name: str = "SORA STUDIO"
    payment_merchant_city: str = "SAO PAULO"
    payment_subscription_ttl_minutes: int = 30
    whatsapp_provider: str = "mock"
    whatsapp_meta_token: str = ""
    whatsapp_meta_phone_number_id: str = ""

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

    # Storage privado (S3/MinIO)
    storage_provider: str = "s3"
    storage_bucket: str = "sora-private"
    storage_region: str = "us-east-1"
    storage_endpoint: str | None = "http://127.0.0.1:9000"
    storage_access_key_id: str = "sora_minio"
    storage_secret_access_key: str = "sora_minio_dev_only"
    storage_presigned_url_ttl_seconds: int = 60
    encryption_key: str = "change-me-encryption-key"


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única (cacheada) das configurações."""
    return Settings()


settings = get_settings()
