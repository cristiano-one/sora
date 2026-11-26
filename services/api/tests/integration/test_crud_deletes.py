"""Exclusão de cadastros com proteção de vínculos e RBAC."""

from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
CLIENTS = "/api/v1/clients"
SERVICES = "/api/v1/services"
USERS = "/api/v1/users"
PLANS = "/api/v1/subscription-plans"
SUBSCRIPTIONS = "/api/v1/subscriptions"
APPOINTMENTS = "/api/v1/appointments"
ACCOUNTS = "/api/v1/finance/accounts"
ENTRIES = "/api/v1/finance/entries"


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


async def _client(auth_client, token: str) -> dict[str, object]:
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {uuid4().hex[:6]}",
            "phone": _phone(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _service(auth_client, token: str, name: str) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": name,
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "100.00",
            "cost": "10.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _appointment(
    auth_client,
    token: str,
    *,
    client_id: object,
    service_id: object,
    collaborator_id: object,
) -> None:
    response = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client_id,
            "service_id": service_id,
            "collaborator_id": str(collaborator_id),
            "starts_at": datetime.combine(
                DAY,
                time(10),
                tzinfo=TZ,
            ).isoformat(),
        },
    )
    assert response.status_code == 201, response.text


async def _plan(
    auth_client,
    token: str,
    service_id: object,
) -> dict[str, object]:
    response = await auth_client.post(
        PLANS,
        headers=_auth(token),
        json={
            "name": f"Plano {uuid4().hex[:6]}",
            "price": "99.90",
            "billing_cycle": "MONTHLY",
            "items": [
                {
                    "service_id": service_id,
                    "uses_per_cycle": 2,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_client_delete_and_conflict(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)

    free = await _client(auth_client, token)
    deleted = await auth_client.delete(
        f"{CLIENTS}/{free['id']}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204

    linked = await _client(auth_client, token)
    service = await _service(auth_client, token, "Corte Delete")
    await _appointment(
        auth_client,
        token,
        client_id=linked["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
    )
    conflict = await auth_client.delete(
        f"{CLIENTS}/{linked['id']}",
        headers=_auth(token),
    )
    assert conflict.status_code == 409


async def test_service_delete_and_conflict(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)

    free = await _service(auth_client, token, "Serviço Livre")
    assert (
        await auth_client.delete(
            f"{SERVICES}/{free['id']}",
            headers=_auth(token),
        )
    ).status_code == 204

    linked = await _service(auth_client, token, "Serviço Vinculado")
    client = await _client(auth_client, token)
    await _appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=linked["id"],
        collaborator_id=collaborator.user_id,
    )
    conflict = await auth_client.delete(
        f"{SERVICES}/{linked['id']}",
        headers=_auth(token),
    )
    assert conflict.status_code == 409


async def test_user_delete_rules(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    suffix = uuid4().hex[:6]
    created = await auth_client.post(
        USERS,
        headers=_auth(token),
        json={
            "full_name": f"Colaborador {suffix}",
            "email": f"colab-{suffix}@example.com",
            "password": "senha-forte-123",
            "role": "COLLABORATOR",
        },
    )
    assert created.status_code == 201, created.text

    deleted = await auth_client.delete(
        f"{USERS}/{created.json()['id']}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204

    self_delete = await auth_client.delete(
        f"{USERS}/{owner.user_id}",
        headers=_auth(token),
    )
    assert self_delete.status_code == 403


async def test_plan_and_subscription_delete(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _service(auth_client, token, "Serviço Plano")
    plan = await _plan(auth_client, token, service["id"])
    client = await _client(auth_client, token)
    subscription = await auth_client.post(
        f"{CLIENTS}/{client['id']}/subscriptions",
        headers=_auth(token),
        json={"plan_id": plan["id"]},
    )
    assert subscription.status_code == 201, subscription.text

    blocked_plan = await auth_client.delete(
        f"{PLANS}/{plan['id']}",
        headers=_auth(token),
    )
    assert blocked_plan.status_code == 409

    blocked_subscription = await auth_client.delete(
        f"{SUBSCRIPTIONS}/{subscription.json()['id']}",
        headers=_auth(token),
    )
    assert blocked_subscription.status_code == 409

    cancelled = await auth_client.post(
        f"{SUBSCRIPTIONS}/{subscription.json()['id']}/cancel",
        headers=_auth(token),
    )
    assert cancelled.status_code == 200

    removed = await auth_client.delete(
        f"{SUBSCRIPTIONS}/{subscription.json()['id']}",
        headers=_auth(token),
    )
    assert removed.status_code == 204

    removed_plan = await auth_client.delete(
        f"{PLANS}/{plan['id']}",
        headers=_auth(token),
    )
    assert removed_plan.status_code == 204


async def test_finance_account_and_entry_delete(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    account = await auth_client.post(
        ACCOUNTS,
        headers=_auth(token),
        json={
            "name": f"Conta {uuid4().hex[:5]}",
            "type": "CASH",
            "initial_balance": "0.00",
        },
    )
    assert account.status_code == 201, account.text
    entry = await auth_client.post(
        ENTRIES,
        headers=_auth(token),
        json={
            "account_id": account.json()["id"],
            "type": "EXPENSE",
            "category": "COMMISSION",
            "description": "Comissão teste",
            "amount": "10.00",
            "competence_date": DAY.isoformat(),
            "cash_date": DAY.isoformat(),
            "status": "PAID",
        },
    )
    assert entry.status_code == 201, entry.text

    blocked = await auth_client.delete(
        f"{ACCOUNTS}/{account.json()['id']}",
        headers=_auth(token),
    )
    assert blocked.status_code == 409

    removed_entry = await auth_client.delete(
        f"{ENTRIES}/{entry.json()['id']}",
        headers=_auth(token),
    )
    assert removed_entry.status_code == 204

    removed_account = await auth_client.delete(
        f"{ACCOUNTS}/{account.json()['id']}",
        headers=_auth(token),
    )
    assert removed_account.status_code == 204


async def test_delete_rbac_and_cross_tenant(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    client = await _client(auth_client, token)

    collaborator_token = await _login(auth_client, collaborator)
    forbidden = await auth_client.delete(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(collaborator_token),
    )
    assert forbidden.status_code == 403

    other_token = await _login(auth_client, auth_user)
    cross = await auth_client.delete(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(other_token),
    )
    assert cross.status_code == 404
