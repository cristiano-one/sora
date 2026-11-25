"""Testes das configurações centralizadas."""

from app.core.config import get_settings, settings


def test_settings_have_expected_defaults() -> None:
    assert settings.app_name == "Sora Studio API"
    assert settings.app_env == "development"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url.startswith("redis://")


def test_get_settings_returns_cached_instance() -> None:
    assert get_settings() is settings
