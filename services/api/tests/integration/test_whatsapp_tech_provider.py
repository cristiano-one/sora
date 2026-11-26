"""Testes do Tech Provider: conexão, RBAC, webhook assinado e isolamento."""

import hashlib
import hmac
import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.core.config import settings
from app.core.crypto import decrypt_text
from app.db.session import create_engine, create_session_factory
from app.integrations.meta_whatsapp import MetaPhoneDetails, MetaWhatsAppError
from app.models import (
    AuditLog,
    TenantWhatsAppAccount,
    UserRole,
    WhatsAppConnectionStatus,
)
from app.modules.whatsapp import service as whatsapp_service
from sqlalchemy import select

pytestmark = [pytest.mark.security, pytest.mark.integration]

CONNECTION = "/api/v1/whatsapp/connection"
WEBHOOK = "/api/v1/whatsapp/webhook"
CONVERSATIONS = "/api/v1/ai/conversations"
LOGIN = "/api/v1/auth/login"


def _phone_number_id() -> str:
    return str(10**14 + uuid4().int % 10**14)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def _patch_meta(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token: str = "EAAB-token-de-teste",
    fail_exchange: bool = False,
    fail_unsubscribe: bool = False,
    fail_register: bool = False,
) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {
        "exchange": [],
        "subscribe": [],
        "unsubscribe": [],
        "details": [],
        "register": [],
    }

    async def fake_exchange(code: str) -> str:
        calls["exchange"].append(code)
        if fail_exchange:
            raise MetaWhatsAppError("Falha simulada na Meta")
        return token

    async def fake_subscribe(waba_id: str, access_token: str) -> None:
        calls["subscribe"].append((waba_id, access_token))

    async def fake_unsubscribe(waba_id: str, access_token: str) -> None:
        calls["unsubscribe"].append((waba_id, access_token))
        if fail_unsubscribe:
            raise MetaWhatsAppError("Falha simulada ao desinscrever")

    async def fake_details(
        phone_number_id: str,
        access_token: str,
    ) -> MetaPhoneDetails:
        calls["details"].append((phone_number_id, access_token))
        return MetaPhoneDetails(
            display_phone_number="+55 11 99999-0000",
            verified_name="Clínica Teste",
            quality_rating="GREEN",
        )

    async def fake_register(
        phone_number_id: str,
        access_token: str,
        pin: str,
    ) -> None:
        calls["register"].append((phone_number_id, access_token, pin))
        if fail_register:
            raise MetaWhatsAppError("Falha simulada no registro")

    monkeypatch.setattr(
        whatsapp_service,
        "exchange_code_for_token",
        fake_exchange,
    )
    monkeypatch.setattr(
        whatsapp_service,
        "subscribe_app_to_waba",
        fake_subscribe,
    )
    monkeypatch.setattr(
        whatsapp_service,
        "unsubscribe_app_from_waba",
        fake_unsubscribe,
    )
    monkeypatch.setattr(
        whatsapp_service,
        "fetch_phone_details",
        fake_details,
    )
    monkeypatch.setattr(
        whatsapp_service,
        "register_phone_number",
        fake_register,
    )
    return calls


async def _connect(
    auth_client: Any,
    token: str,
    *,
    phone_number_id: str,
    waba_id: str = "123456789012345",
    pin: str = "123456",
) -> Any:
    return await auth_client.post(
        CONNECTION,
        headers=_auth(token),
        json={
            "code": "codigo-de-teste-123456",
            "waba_id": waba_id,
            "phone_number_id": phone_number_id,
            "pin": pin,
        },
    )


async def _account(
    database_urls: dict[str, str],
    tenant_id: UUID,
) -> TenantWhatsAppAccount | None:
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            return await session.get(TenantWhatsAppAccount, tenant_id)
    finally:
        await engine.dispose()


def _payload(
    *,
    phone_number_id: str,
    phone: str,
    text: str,
    message_id: str,
) -> dict[str, object]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5511999990000",
                                "phone_number_id": phone_number_id,
                            },
                            "messages": [
                                {
                                    "from": phone,
                                    "id": message_id,
                                    "timestamp": "1764200000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _signed(
    payload: dict[str, object],
    secret: str,
) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={digest}",
    }


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    secret = "segredo-do-app-de-teste"
    monkeypatch.setattr(settings, "whatsapp_app_secret", secret)
    monkeypatch.setattr(settings, "whatsapp_app_id", "1234567890")
    monkeypatch.setattr(settings, "whatsapp_config_id", "987654321")
    monkeypatch.setattr(settings, "whatsapp_verify_token", "verify-de-teste")
    yield secret


async def test_owner_connects_encrypts_token_and_never_returns_it(
    auth_client,
    tenant_users,
    database_urls,
    webhook_secret,
    monkeypatch,
) -> None:
    calls = _patch_meta(monkeypatch)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    phone_number_id = _phone_number_id()

    response = await _connect(
        auth_client,
        owner,
        phone_number_id=phone_number_id,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CONNECTED"
    assert body["display_phone_number"] == "+55 11 99999-0000"
    assert body["verified_name"] == "Clínica Teste"
    assert body["quality_rating"] == "GREEN"
    assert body["registration_status"] == "REGISTERED"
    assert body["registration_error"] is None
    assert body["embedded_signup"]["enabled"] is True
    assert "access_token" not in json.dumps(body)
    assert "EAAB-token-de-teste" not in response.text

    assert calls["exchange"] == ["codigo-de-teste-123456"]
    assert calls["subscribe"] == [
        ("123456789012345", "EAAB-token-de-teste")
    ]
    assert calls["register"] == [
        (phone_number_id, "EAAB-token-de-teste", "123456")
    ]

    account = await _account(database_urls, tenant_users.tenant_id)
    assert account is not None
    assert account.status is WhatsAppConnectionStatus.CONNECTED
    assert account.phone_number_id == phone_number_id
    assert account.connected_by == tenant_users.users[UserRole.OWNER].user_id
    assert account.access_token_encrypted is not None
    assert account.access_token_encrypted != "EAAB-token-de-teste"
    assert decrypt_text(account.access_token_encrypted) == "EAAB-token-de-teste"
    assert account.registration_status.value == "REGISTERED"
    assert account.registration_pin_encrypted is not None
    assert decrypt_text(account.registration_pin_encrypted) == "123456"

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    try:
        async with factory() as audit_session:
            audit = await audit_session.scalar(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_users.tenant_id,
                    AuditLog.action == "whatsapp.connect",
                )
            )
            assert audit is not None
            assert set((audit.details or {}).keys()) == {
                "waba_id",
                "phone_number_id",
            }
    finally:
        await engine.dispose()

    admin = await _login(
        auth_client,
        tenant_users.users[UserRole.ADMIN],
    )
    read = await auth_client.get(CONNECTION, headers=_auth(admin))
    assert read.status_code == 200
    assert read.json()["status"] == "CONNECTED"
    assert "EAAB-token-de-teste" not in read.text


async def test_connection_rbac_and_cross_tenant_isolation(
    auth_client,
    tenant_users,
    auth_user,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    admin = await _login(
        auth_client,
        tenant_users.users[UserRole.ADMIN],
    )
    collaborator = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    phone_number_id = _phone_number_id()
    connected = await _connect(
        auth_client,
        owner,
        phone_number_id=phone_number_id,
    )
    assert connected.status_code == 200, connected.text

    forbidden_connect = await _connect(
        auth_client,
        admin,
        phone_number_id=_phone_number_id(),
    )
    assert forbidden_connect.status_code == 403
    forbidden_read = await auth_client.get(
        CONNECTION,
        headers=_auth(collaborator),
    )
    assert forbidden_read.status_code == 403
    forbidden_delete = await auth_client.delete(
        CONNECTION,
        headers=_auth(admin),
    )
    assert forbidden_delete.status_code == 403

    other_owner = await _login(auth_client, auth_user)
    other_read = await auth_client.get(
        CONNECTION,
        headers=_auth(other_owner),
    )
    assert other_read.status_code == 200
    assert other_read.json()["status"] == "DISCONNECTED"
    assert other_read.json()["phone_number_id"] is None

    conflict = await _connect(
        auth_client,
        other_owner,
        phone_number_id=phone_number_id,
    )
    assert conflict.status_code == 409
    assert other_read.json()["display_phone_number"] is None


async def test_disconnect_clears_credentials_even_if_meta_fails(
    auth_client,
    tenant_users,
    database_urls,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch, fail_unsubscribe=True)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    assert (
        await _connect(
            auth_client,
            owner,
            phone_number_id=_phone_number_id(),
        )
    ).status_code == 200

    response = await auth_client.delete(
        CONNECTION,
        headers=_auth(owner),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISCONNECTED"
    assert response.json()["phone_number_id"] is None

    account = await _account(database_urls, tenant_users.tenant_id)
    assert account is not None
    assert account.status is WhatsAppConnectionStatus.DISCONNECTED
    assert account.access_token_encrypted is None
    assert account.registration_pin_encrypted is None
    assert account.registration_status.value == "PENDING"
    assert account.waba_id is None
    assert account.phone_number_id is None


async def test_meta_failure_does_not_persist_connection(
    auth_client,
    tenant_users,
    database_urls,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch, fail_exchange=True)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    response = await _connect(
        auth_client,
        owner,
        phone_number_id=_phone_number_id(),
    )
    assert response.status_code == 502
    assert "token" not in response.text.lower()
    assert await _account(database_urls, tenant_users.tenant_id) is None


async def test_webhook_verification_challenge(
    auth_client,
    webhook_secret,
) -> None:
    response = await auth_client.get(
        WEBHOOK,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-de-teste",
            "hub.challenge": "desafio-123",
        },
    )
    assert response.status_code == 200
    assert response.text == "desafio-123"

    wrong = await auth_client.get(
        WEBHOOK,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "errado",
            "hub.challenge": "desafio-123",
        },
    )
    assert wrong.status_code == 403


async def test_signed_webhook_routes_by_phone_and_is_idempotent(
    auth_client,
    tenant_users,
    auth_user,
    webhook_secret,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch)
    sent: list[dict[str, object]] = []

    async def fake_send(**kwargs: object) -> bool:
        sent.append(kwargs)
        return True

    monkeypatch.setattr(
        "app.modules.ai.service.send_whatsapp_message",
        fake_send,
    )

    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    other_owner = await _login(auth_client, auth_user)
    phone_a = _phone_number_id()
    phone_b = _phone_number_id()
    assert (
        await _connect(auth_client, owner, phone_number_id=phone_a)
    ).status_code == 200
    assert (
        await _connect(auth_client, other_owner, phone_number_id=phone_b)
    ).status_code == 200

    customer_phone = f"119{uuid4().int % 10**8:08d}"
    payload = _payload(
        phone_number_id=phone_a,
        phone=customer_phone,
        text="Oi, quero agendar um horário",
        message_id="wamid.teste-1",
    )
    body, headers = _signed(payload, webhook_secret)
    response = await auth_client.post(WEBHOOK, content=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}

    conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(owner),
    )
    assert conversations.status_code == 200
    assert any(
        item["phone"] == customer_phone for item in conversations.json()
    )
    other_conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(other_owner),
    )
    assert other_conversations.status_code == 200
    assert all(
        item["phone"] != customer_phone
        for item in other_conversations.json()
    )

    assert len(sent) == 1
    credentials = sent[0]["credentials"]
    assert credentials.phone_number_id == phone_a
    assert credentials.access_token == "EAAB-token-de-teste"

    # Reenvio do mesmo message_id não duplica a mensagem nem responde de novo.
    replay = await auth_client.post(WEBHOOK, content=body, headers=headers)
    assert replay.status_code == 200
    assert len(sent) == 1
    conversation_id = conversations.json()[0]["id"]
    detail = await auth_client.get(
        f"{CONVERSATIONS}/{conversation_id}",
        headers=_auth(owner),
    )
    assert detail.status_code == 200
    inbound = [
        item
        for item in detail.json()["messages"]
        if item["direction"] == "INBOUND"
        and item["content"] == "Oi, quero agendar um horário"
    ]
    assert len(inbound) == 1


async def test_webhook_rejects_invalid_signature_and_ignores_unknown_phone(
    auth_client,
    tenant_users,
    webhook_secret,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    phone_number_id = _phone_number_id()
    assert (
        await _connect(auth_client, owner, phone_number_id=phone_number_id)
    ).status_code == 200

    payload = _payload(
        phone_number_id=phone_number_id,
        phone=f"119{uuid4().int % 10**8:08d}",
        text="Oi",
        message_id="wamid.assinatura",
    )
    body, headers = _signed(payload, "segredo-errado")
    invalid = await auth_client.post(WEBHOOK, content=body, headers=headers)
    assert invalid.status_code == 403

    unknown = _payload(
        phone_number_id=_phone_number_id(),
        phone=f"119{uuid4().int % 10**8:08d}",
        text="Oi",
        message_id="wamid.desconhecido",
    )
    body, headers = _signed(unknown, webhook_secret)
    ignored = await auth_client.post(WEBHOOK, content=body, headers=headers)
    assert ignored.status_code == 200
    conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(owner),
    )
    assert conversations.json() == []


async def test_registration_failure_keeps_connection_with_warning(
    auth_client,
    tenant_users,
    database_urls,
    webhook_secret,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch, fail_register=True)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    response = await _connect(
        auth_client,
        owner,
        phone_number_id=_phone_number_id(),
        pin="654321",
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CONNECTED"
    assert body["registration_status"] == "FAILED"
    assert "Registro na Cloud API não confirmado" in body["registration_error"]

    account = await _account(database_urls, tenant_users.tenant_id)
    assert account is not None
    assert account.status is WhatsAppConnectionStatus.CONNECTED
    assert account.registration_status.value == "FAILED"
    assert account.registration_pin_encrypted is None


async def test_connect_requires_six_digit_pin(
    auth_client,
    tenant_users,
    monkeypatch,
) -> None:
    _patch_meta(monkeypatch)
    owner = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    response = await _connect(
        auth_client,
        owner,
        phone_number_id=_phone_number_id(),
        pin="12ab",
    )
    assert response.status_code == 422
