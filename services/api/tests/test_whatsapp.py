"""Testes dos adapters de WhatsApp (sem chamadas externas reais)."""

import pytest
from app.core.config import settings
from app.core.whatsapp import send_whatsapp_message

pytestmark = [pytest.mark.security]


async def test_mock_provider_accepts_message(monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_provider", "mock")
    assert await send_whatsapp_message(phone="5511999999999", text="oi")


async def test_meta_without_credentials_fails_safely(monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_provider", "meta")
    monkeypatch.setattr(settings, "whatsapp_meta_token", "")
    monkeypatch.setattr(settings, "whatsapp_meta_phone_number_id", "")
    assert not await send_whatsapp_message(phone="5511999999999", text="oi")
