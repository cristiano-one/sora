"""Testes das configurações centralizadas."""

import pytest
from app.core.config import Settings, get_settings, settings


def test_settings_have_expected_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida os defaults da classe, independentemente do ambiente do CI."""
    for variable in ("APP_NAME", "APP_ENV", "DATABASE_URL", "REDIS_URL"):
        monkeypatch.delenv(variable, raising=False)

    fresh = Settings(_env_file=None)

    assert fresh.app_name == "Sora Studio API"
    assert fresh.app_env == "development"
    assert fresh.database_url.startswith("postgresql+asyncpg://")
    assert fresh.redis_url.startswith("redis://")


def test_get_settings_returns_cached_instance() -> None:
    assert get_settings() is settings
