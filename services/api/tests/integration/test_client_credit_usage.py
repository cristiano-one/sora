"""Uso de créditos de aniversário no prontuário do cliente."""

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
RUN_CREDITS = "/api/v1/ai/birthday-credits/run"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def _credit(auth_client, tenant_users) -> tuple[str, dict, str]:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={"birthday_credit_amount": "50.00"},
    )
    birth = (TODAY + timedelta(days=2)).replace(year=1994)
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Crédito {uuid4().hex[:6]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
            "birth_date": birth.isoformat(),
        },
    )
    assert client.status_code == 201, client.text
    run = await auth_client.post(RUN_CREDITS, headers=_auth(token))
    assert run.status_code == 200, run.text
    credits = await auth_client.get(
        f"{CLIENTS}/{client.json()['id']}/credits",
        headers=_auth(token),
    )
    assert credits.status_code == 200, credits.text
    credit = next(
        item for item in credits.json() if item["reason"] == "BIRTHDAY"
    )
    assert credit["amount"] == "50.00"
    return token, client.json(), credit


async def test_credit_can_be_used_partially_and_tracks_history(
    auth_client,
    tenant_users,
) -> None:
    token, client, credit = await _credit(auth_client, tenant_users)
    used = await auth_client.post(
        f"{CLIENTS}/{client['id']}/credits/{credit['id']}/use",
        headers=_auth(token),
        json={"amount": "20.00", "note": "Abatimento no atendimento"},
    )
    assert used.status_code == 201, used.text
    assert used.json()["amount"] == "20.00"

    credits = await auth_client.get(
        f"{CLIENTS}/{client['id']}/credits",
        headers=_auth(token),
    )
    updated = next(
        item for item in credits.json() if item["id"] == credit["id"]
    )
    assert updated["used_amount"] == "20.00"
    assert updated["remaining_amount"] == "30.00"
    assert updated["is_available"] is True

    over = await auth_client.post(
        f"{CLIENTS}/{client['id']}/credits/{credit['id']}/use",
        headers=_auth(token),
        json={"amount": "40.00"},
    )
    assert over.status_code == 422

    final = await auth_client.post(
        f"{CLIENTS}/{client['id']}/credits/{credit['id']}/use",
        headers=_auth(token),
        json={"amount": "30.00"},
    )
    assert final.status_code == 201

    usages = await auth_client.get(
        f"{CLIENTS}/{client['id']}/credit-usages",
        headers=_auth(token),
    )
    assert usages.status_code == 200
    assert len(usages.json()) == 2

    exhausted = await auth_client.post(
        f"{CLIENTS}/{client['id']}/credits/{credit['id']}/use",
        headers=_auth(token),
        json={"amount": "1.00"},
    )
    assert exhausted.status_code == 422


async def test_credit_usage_is_manager_only_and_cross_tenant_hidden(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    _token, client, credit = await _credit(auth_client, tenant_users)

    collaborator_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    forbidden = await auth_client.get(
        f"{CLIENTS}/{client['id']}/credits",
        headers=_auth(collaborator_token),
    )
    assert forbidden.status_code == 403

    other_token = await _login(auth_client, auth_user)
    cross = await auth_client.post(
        f"{CLIENTS}/{client['id']}/credits/{credit['id']}/use",
        headers=_auth(other_token),
        json={"amount": "10.00"},
    )
    assert cross.status_code == 404
