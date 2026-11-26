"""Testes dos adapters de WhatsApp (sem chamadas externas reais)."""

from typing import ClassVar

import pytest
from app.core.config import settings
from app.core.meta_signature import (
    verify_meta_signature,
    verify_meta_verify_token,
)
from app.core.whatsapp import WhatsAppCredentials, send_whatsapp_message

pytestmark = [pytest.mark.security]


async def test_mock_provider_accepts_message(monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_provider", "mock")
    assert await send_whatsapp_message(phone="5511999999999", text="oi")


async def test_meta_without_credentials_fails_safely(monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_provider", "meta")
    monkeypatch.setattr(settings, "whatsapp_meta_token", "")
    monkeypatch.setattr(settings, "whatsapp_meta_phone_number_id", "")
    assert not await send_whatsapp_message(phone="5511999999999", text="oi")


def _signature(secret: str, body: bytes) -> str:
    import hashlib
    import hmac

    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_meta_signature_accepts_valid_and_rejects_invalid() -> None:
    body = b'{"object":"whatsapp_business_account"}'
    signature = _signature("app-secret", body)
    assert verify_meta_signature(
        raw_body=body,
        signature_header=signature,
        app_secret="app-secret",
    )
    assert not verify_meta_signature(
        raw_body=body,
        signature_header=signature,
        app_secret="outro-segredo",
    )
    assert not verify_meta_signature(
        raw_body=body,
        signature_header="",
        app_secret="app-secret",
    )


def test_meta_signature_fails_closed_without_secret() -> None:
    body = b"{}"
    assert not verify_meta_signature(
        raw_body=body,
        signature_header=_signature("", body),
        app_secret="",
    )


def test_meta_verify_token_uses_constant_time_and_rejects_empty() -> None:
    assert verify_meta_verify_token("token", "token")
    assert not verify_meta_verify_token("token", "outro")
    assert not verify_meta_verify_token("", "")
    assert not verify_meta_verify_token("qualquer", "")


class _FakeResponse:
    is_success = True


class _FakeAsyncClient:
    calls: ClassVar[list[dict[str, object]]] = []

    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> _FakeResponse:
        self.calls.append(
            {"url": url, "headers": headers, "json": json}
        )
        return _FakeResponse()


async def test_tenant_credentials_are_used_for_sending(monkeypatch) -> None:
    import app.core.whatsapp as whatsapp_module

    _FakeAsyncClient.calls = []
    monkeypatch.setattr(
        whatsapp_module.httpx,
        "AsyncClient",
        _FakeAsyncClient,
    )
    sent = await send_whatsapp_message(
        phone="5511999999999",
        text="oi",
        credentials=WhatsAppCredentials(
            phone_number_id="123456",
            access_token="token-da-clinica",
        ),
    )
    assert sent
    call = _FakeAsyncClient.calls[-1]
    assert "123456/messages" in str(call["url"])
    assert call["headers"] == {
        "Authorization": "Bearer token-da-clinica",
    }


def _meta_payload(message: dict[str, object]) -> dict[str, object]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "123"},
                            "messages": [message],
                        },
                    }
                ]
            }
        ],
    }


def test_parse_inbound_text_and_interactive_reply() -> None:
    from app.modules.whatsapp.webhook import parse_inbound_messages

    text = parse_inbound_messages(
        _meta_payload(
            {
                "from": "5511999999999",
                "id": "wamid.1",
                "type": "text",
                "text": {"body": "Oi"},
            }
        )
    )
    assert len(text) == 1
    assert text[0].phone == "5511999999999"
    assert text[0].text == "Oi"
    assert text[0].external_id == "wamid.1"

    interactive = parse_inbound_messages(
        _meta_payload(
            {
                "from": "5511999999999",
                "id": "wamid.2",
                "type": "interactive",
                "interactive": {
                    "button_reply": {"id": "b1", "title": "Quero agendar"}
                },
            }
        )
    )
    assert len(interactive) == 1
    assert interactive[0].text == "Quero agendar"


def test_parse_inbound_ignores_statuses_and_invalid_phone() -> None:
    from app.modules.whatsapp.webhook import parse_inbound_messages

    status_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "123"},
                            "statuses": [{"id": "wamid.1", "status": "delivered"}],
                        },
                    }
                ]
            }
        ],
    }
    assert parse_inbound_messages(status_payload) == []
    assert (
        parse_inbound_messages(
            _meta_payload(
                {
                    "from": "123",
                    "id": "wamid.3",
                    "type": "text",
                    "text": {"body": "Oi"},
                }
            )
        )
        == []
    )
