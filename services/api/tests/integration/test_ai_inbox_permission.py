"""Testes do inbox da SORA IA no mobile: permissão, RBAC e isolamento."""

from typing import Any
from uuid import uuid4

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
USERS = "/api/v1/users"
SIMULATE = "/api/v1/ai/whatsapp/simulate"
CONVERSATIONS = "/api/v1/ai/conversations"
SUMMARY = "/api/v1/ai/summary"
WHATSAPP = "/api/v1/whatsapp/connection"


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


async def _set_inbox_permission(
    auth_client: Any,
    owner_token: str,
    user_id: Any,
    allowed: bool,
) -> Any:
    return await auth_client.patch(
        f"{USERS}/{user_id}",
        headers=_auth(owner_token),
        json={"can_manage_ai_inbox": allowed},
    )


async def test_collaborator_needs_explicit_inbox_permission(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    admin = tenant_users.users[UserRole.ADMIN]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    owner_token = await _login(auth_client, owner)
    admin_token = await _login(auth_client, admin)
    collaborator_token = await _login(auth_client, collaborator)
    phone = _phone()

    created = await auth_client.post(
        SIMULATE,
        headers=_auth(owner_token),
        json={"phone": phone, "text": "Olá"},
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    denied = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(collaborator_token),
    )
    assert denied.status_code == 403
    denied_summary = await auth_client.get(
        SUMMARY,
        headers=_auth(collaborator_token),
    )
    assert denied_summary.status_code == 403
    denied_whatsapp = await auth_client.get(
        WHATSAPP,
        headers=_auth(collaborator_token),
    )
    assert denied_whatsapp.status_code == 403

    granted = await _set_inbox_permission(
        auth_client,
        owner_token,
        collaborator.user_id,
        True,
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["can_manage_ai_inbox"] is True

    me = await auth_client.get(ME, headers=_auth(collaborator_token))
    assert me.status_code == 200
    assert me.json()["can_manage_ai_inbox"] is True

    summary = await auth_client.get(
        SUMMARY,
        headers=_auth(collaborator_token),
    )
    assert summary.status_code == 200
    conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(collaborator_token),
    )
    assert conversations.status_code == 200
    assert any(item["phone"] == phone for item in conversations.json())

    detail = await auth_client.get(
        f"{CONVERSATIONS}/{conversation_id}",
        headers=_auth(collaborator_token),
    )
    assert detail.status_code == 200
    assert detail.json()["phone"] == phone

    takeover = await auth_client.post(
        f"{CONVERSATIONS}/{conversation_id}/takeover",
        headers=_auth(collaborator_token),
    )
    assert takeover.status_code == 200, takeover.text
    assert takeover.json()["status"] == "HUMAN"

    reply = await auth_client.post(
        f"{CONVERSATIONS}/{conversation_id}/messages",
        headers=_auth(collaborator_token),
        json={"content": "Olá! Como posso ajudar?"},
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["direction"] == "OUTBOUND"

    closed = await auth_client.post(
        f"{CONVERSATIONS}/{conversation_id}/close",
        headers=_auth(collaborator_token),
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    # ADMIN já tem acesso por papel, mas não deve conseguir abrir WhatsApp/Meta.
    admin_conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(admin_token),
    )
    assert admin_conversations.status_code == 200
    admin_whatsapp = await auth_client.get(
        WHATSAPP,
        headers=_auth(admin_token),
    )
    assert admin_whatsapp.status_code == 200


async def test_revoked_permission_blocks_next_request(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    owner_token = await _login(auth_client, owner)
    collaborator_token = await _login(auth_client, collaborator)
    assert (
        await _set_inbox_permission(
            auth_client,
            owner_token,
            collaborator.user_id,
            True,
        )
    ).status_code == 200
    assert (
        await auth_client.get(
            CONVERSATIONS,
            headers=_auth(collaborator_token),
        )
    ).status_code == 200

    assert (
        await _set_inbox_permission(
            auth_client,
            owner_token,
            collaborator.user_id,
            False,
        )
    ).status_code == 200
    denied = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(collaborator_token),
    )
    assert denied.status_code == 403
    me = await auth_client.get(ME, headers=_auth(collaborator_token))
    assert me.json()["can_manage_ai_inbox"] is False


async def test_inbox_permission_does_not_cross_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner_a = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    owner_a_token = await _login(auth_client, owner_a)
    collaborator_token = await _login(auth_client, collaborator)
    other_owner_token = await _login(auth_client, auth_user)
    assert (
        await _set_inbox_permission(
            auth_client,
            owner_a_token,
            collaborator.user_id,
            True,
        )
    ).status_code == 200

    phone_b = _phone()
    created_b = await auth_client.post(
        SIMULATE,
        headers=_auth(other_owner_token),
        json={"phone": phone_b, "text": "Olá"},
    )
    assert created_b.status_code == 200, created_b.text

    conversations = await auth_client.get(
        CONVERSATIONS,
        headers=_auth(collaborator_token),
    )
    assert conversations.status_code == 200
    assert all(item["phone"] != phone_b for item in conversations.json())


async def test_create_collaborator_with_inbox_permission(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    owner_token = await _login(auth_client, owner)
    suffix = uuid4().hex[:8]
    response = await auth_client.post(
        USERS,
        headers=_auth(owner_token),
        json={
            "full_name": "Recepção",
            "email": f"recepcao-{suffix}@example.com",
            "password": "senha-forte-123",
            "role": "COLLABORATOR",
            "can_manage_ai_inbox": True,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["can_manage_ai_inbox"] is True


async def test_inbox_checkins_show_all_professionals_for_reception(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    from datetime import UTC, datetime, time, timedelta
    from zoneinfo import ZoneInfo

    from app.db.session import create_engine, create_session_factory
    from app.models import Appointment

    tz = ZoneInfo("America/Sao_Paulo")
    day = datetime.now(tz).date() + timedelta(days=1)
    starts_at = datetime.combine(day, time(10), tzinfo=tz)
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    owner_token = await _login(auth_client, owner)
    collaborator_token = await _login(auth_client, collaborator)
    assert (
        await _set_inbox_permission(
            auth_client,
            owner_token,
            collaborator.user_id,
            True,
        )
    ).status_code == 200

    suffix = uuid4().hex[:8]
    service = await auth_client.post(
        "/api/v1/services",
        headers=_auth(owner_token),
        json={
            "name": f"Recepção {suffix}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "120.00",
            "cost": "20.00",
            "show_average_price": True,
        },
    )
    assert service.status_code == 201, service.text
    client = await auth_client.post(
        "/api/v1/clients",
        headers=_auth(owner_token),
        json={"full_name": "Cliente Recepção", "phone": _phone()},
    )
    assert client.status_code == 201, client.text
    appointment = await auth_client.post(
        "/api/v1/appointments",
        headers=_auth(owner_token),
        json={
            "client_id": client.json()["id"],
            "service_id": service.json()["id"],
            "collaborator_id": str(owner.user_id),
            "starts_at": starts_at.isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            row = await session.get(Appointment, appointment.json()["id"])
            assert row is not None
            row.checked_in_at = datetime.now(UTC)
            await session.commit()
    finally:
        await engine.dispose()

    response = await auth_client.get(
        f"/api/v1/ai/inbox/checkins?date={day.isoformat()}",
        headers=_auth(collaborator_token),
    )
    assert response.status_code == 200, response.text
    assert any(
        item["client_name"] == "Cliente Recepção"
        and item["collaborator_name"]
        for item in response.json()
    )
