"""Testes do provedor Groq: chave cifrada, RBAC, teste e fallback seguro."""

from typing import Any
from uuid import uuid4

import pytest
from app.core.crypto import decrypt_text
from app.db.session import create_engine, create_session_factory
from app.integrations.groq import GroqError
from app.models import TenantSettings, UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
SETTINGS = "/api/v1/tenants/settings"
SIMULATE = "/api/v1/ai/whatsapp/simulate"
PROVIDER_TEST = "/api/v1/ai/provider/test"
MODEL = "llama-3.3-70b-versatile"
KEY = "gsk_teste_1234567890"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _phone() -> str:
    return f"119{uuid4().int % 10**8:08d}"


async def _login(auth_client: Any, user: Any) -> str:
    response = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": user.tenant_slug,
            "email": user.email,
            "password": user.password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _configure_groq(
    auth_client: Any,
    token: str,
    *,
    key: str = KEY,
) -> Any:
    return await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={
            "ai_provider": "groq",
            "ai_model": MODEL,
            "ai_api_key": key,
        },
    )


async def _settings_row(
    database_urls: dict[str, str],
    tenant_id: Any,
) -> TenantSettings | None:
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            return await session.get(TenantSettings, tenant_id)
    finally:
        await engine.dispose()


async def test_owner_saves_encrypted_groq_key_and_admin_cannot_change_it(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    response = await _configure_groq(auth_client, owner)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_provider"] == "groq"
    assert body["ai_model"] == MODEL
    assert body["ai_key_configured"] is True
    assert KEY not in response.text
    assert "ai_api_key" not in body

    row = await _settings_row(database_urls, tenant_users.tenant_id)
    assert row is not None
    assert row.ai_api_key_encrypted is not None
    assert row.ai_api_key_encrypted != KEY
    assert decrypt_text(row.ai_api_key_encrypted) == KEY

    read = await auth_client.get(SETTINGS, headers=_auth(owner))
    assert read.status_code == 200
    assert read.json()["ai_key_configured"] is True
    assert KEY not in read.text

    admin = await _login(
        auth_client,
        tenant_users.users[UserRole.ADMIN],
    )
    forbidden = await auth_client.patch(
        SETTINGS,
        headers=_auth(admin),
        json={"ai_provider": "mock"},
    )
    assert forbidden.status_code == 403
    allowed = await auth_client.patch(
        SETTINGS,
        headers=_auth(admin),
        json={"agent_name": "Bia"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["agent_name"] == "Bia"
    assert allowed.json()["ai_provider"] == "groq"


async def test_groq_requires_key_and_clear_switches_to_mock(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    missing = await auth_client.patch(
        SETTINGS,
        headers=_auth(owner),
        json={"ai_provider": "groq", "ai_model": MODEL},
    )
    assert missing.status_code == 422

    assert (await _configure_groq(auth_client, owner)).status_code == 200
    ambiguous = await auth_client.patch(
        SETTINGS,
        headers=_auth(owner),
        json={"clear_ai_api_key": True, "ai_api_key": "gsk_nova"},
    )
    assert ambiguous.status_code == 422

    cleared = await auth_client.patch(
        SETTINGS,
        headers=_auth(owner),
        json={"ai_provider": "mock", "clear_ai_api_key": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["ai_key_configured"] is False
    assert cleared.json()["ai_provider"] == "mock"

    row = await _settings_row(database_urls, tenant_users.tenant_id)
    assert row is not None
    assert row.ai_api_key_encrypted is None


async def test_groq_settings_are_isolated_between_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    assert (await _configure_groq(auth_client, owner)).status_code == 200

    other_owner = await _login(auth_client, auth_user)
    other = await auth_client.get(SETTINGS, headers=_auth(other_owner))
    assert other.status_code == 200
    assert other.json()["ai_provider"] == "mock"
    assert other.json()["ai_key_configured"] is False
    assert KEY not in other.text


async def test_provider_test_endpoint_uses_saved_key_without_leaking_it(
    auth_client,
    tenant_users,
    monkeypatch,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    assert (await _configure_groq(auth_client, owner)).status_code == 200
    calls: list[dict[str, object]] = []

    async def fake_chat(**kwargs: object) -> str:
        calls.append(kwargs)
        return "OK"

    monkeypatch.setattr("app.modules.ai.llm.chat_completion", fake_chat)
    response = await auth_client.post(PROVIDER_TEST, headers=_auth(owner))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["provider"] == "groq"
    assert body["model"] == MODEL
    assert body["reply"] == "OK"
    assert body["latency_ms"] >= 0
    assert KEY not in response.text
    assert calls and calls[0]["api_key"] == KEY

    async def failing_chat(**kwargs: object) -> str:
        raise GroqError("Limite de uso da Groq atingido.")

    monkeypatch.setattr(
        "app.modules.ai.llm.chat_completion",
        failing_chat,
    )
    failed = await auth_client.post(PROVIDER_TEST, headers=_auth(owner))
    assert failed.status_code == 502
    assert "Limite de uso" in failed.text

    admin = await _login(
        auth_client,
        tenant_users.users[UserRole.ADMIN],
    )
    forbidden = await auth_client.post(
        PROVIDER_TEST,
        headers=_auth(admin),
    )
    assert forbidden.status_code == 403


async def test_groq_rewrites_simulator_reply_and_fallback_is_safe(
    auth_client,
    tenant_users,
    monkeypatch,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    assert (await _configure_groq(auth_client, owner)).status_code == 200
    phone = _phone()

    async def fake_chat(**kwargs: object) -> str:
        return "Oi! Sou a Sora da Clínica RBAC. Como posso ajudar hoje?"

    monkeypatch.setattr("app.modules.ai.llm.chat_completion", fake_chat)
    simulated = await auth_client.post(
        SIMULATE,
        headers=_auth(owner),
        json={"phone": phone, "text": "Olá"},
    )
    assert simulated.status_code == 200, simulated.text
    assert simulated.json()["intent"] == "greeting"
    assert "Como posso ajudar hoje" in simulated.json()["reply"]

    async def failing_chat(**kwargs: object) -> str:
        raise GroqError("Groq fora do ar")

    monkeypatch.setattr(
        "app.modules.ai.llm.chat_completion",
        failing_chat,
    )
    fallback = await auth_client.post(
        SIMULATE,
        headers=_auth(owner),
        json={"phone": _phone(), "text": "Olá"},
    )
    assert fallback.status_code == 200
    assert fallback.json()["intent"] == "greeting"
    assert "Como posso ajudar hoje" not in fallback.json()["reply"]
    assert "Sora" in fallback.json()["reply"]


async def test_groq_never_receives_real_magic_link(
    auth_client,
    tenant_users,
    monkeypatch,
) -> None:
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    assert (await _configure_groq(auth_client, owner)).status_code == 200
    calls: list[dict[str, object]] = []

    async def fake_chat(**kwargs: object) -> str:
        calls.append(kwargs)
        return "Claro! Escolha seu horário em {{BOOKING_LINK}}"

    monkeypatch.setattr("app.modules.ai.llm.chat_completion", fake_chat)
    response = await auth_client.post(
        SIMULATE,
        headers=_auth(owner),
        json={"phone": _phone(), "text": "Quero agendar um horário"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"] == "booking"
    assert "{{BOOKING_LINK}}" not in body["reply"]
    assert "/public/" in body["reply"]
    assert calls
    messages = calls[0]["messages"]
    prompt = messages[0]["content"]  # type: ignore[index]
    assert "{{BOOKING_LINK}}" in prompt
    assert "/public/" not in prompt

    async def evil_chat(**kwargs: object) -> str:
        return "Claro! Agende aqui: https://golpe.example/agenda"

    monkeypatch.setattr("app.modules.ai.llm.chat_completion", evil_chat)
    rejected = await auth_client.post(
        SIMULATE,
        headers=_auth(owner),
        json={"phone": _phone(), "text": "Quero agendar um horário"},
    )
    assert rejected.status_code == 200, rejected.text
    assert "golpe.example" not in rejected.json()["reply"]
    assert "/public/" in rejected.json()["reply"]
