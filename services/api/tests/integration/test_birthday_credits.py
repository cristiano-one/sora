"""Créditos de aniversário: idempotência, RBAC e isolamento."""

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime.now(TZ).date()
LOGIN = "/api/v1/auth/login"
CLIENTS = "/api/v1/clients"
SETTINGS = "/api/v1/tenants/settings"
CREDITS = "/api/v1/ai/birthday-credits"
RUN = "/api/v1/ai/birthday-credits/run"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _phone() -> str:
    return f"119{uuid4().int % 10**8:08d}"


async def _login(auth_client, user) -> str:
    response = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": user.tenant_slug,
            "email": user.email,
            "password": user.password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _birthday_client(auth_client, token: str) -> dict[str, object]:
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Aniversariante {uuid4().hex[:6]}",
            "phone": _phone(),
            "birth_date": (TODAY + timedelta(days=2))
            .replace(year=1995)
            .isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _set_credit_amount(auth_client, token: str, amount: str) -> None:
    response = await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={"birthday_credit_amount": amount},
    )
    assert response.status_code == 200, response.text


async def test_birthday_credits_are_idempotent(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    await _set_credit_amount(auth_client, token, "25.00")
    client = await _birthday_client(auth_client, token)

    first = await auth_client.post(RUN, headers=_auth(token))
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["created"] == 1
    assert body["total_amount"] == "25.00"
    assert body["credits"][0]["client_id"] == client["id"]
    assert body["credits"][0]["used_amount"] == "0.00"

    second = await auth_client.post(RUN, headers=_auth(token))
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["total_amount"] == "0.00"

    listed = await auth_client.get(
        CREDITS,
        headers=_auth(token),
        params={"year": str(TODAY.year)},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["amount"] == "25.00"


async def test_birthday_credits_disabled_by_default(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    await _birthday_client(auth_client, token)

    response = await auth_client.post(RUN, headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["created"] == 0
    assert response.json()["credits"] == []


async def test_birthday_credits_require_manager(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, collaborator)

    assert (await auth_client.get(CREDITS, headers=_auth(token))).status_code == 403
    assert (await auth_client.post(RUN, headers=_auth(token))).status_code == 403


async def test_birthday_credits_are_isolated_between_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    await _set_credit_amount(auth_client, token, "30.00")
    await _birthday_client(auth_client, token)
    created = await auth_client.post(RUN, headers=_auth(token))
    assert created.json()["created"] == 1

    other_token = await _login(auth_client, auth_user)
    listed = await auth_client.get(CREDITS, headers=_auth(other_token))
    assert listed.status_code == 200
    assert listed.json() == []
