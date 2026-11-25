"""Testes de assinaturas de clientes, cotas e isolamento multi-tenant."""

from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from app.core.config import settings
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
PLANS = "/api/v1/subscription-plans"
SUBSCRIPTIONS = "/api/v1/subscriptions"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _internal() -> dict[str, str]:
    return {"X-Internal-Token": settings.internal_api_token}


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


async def _create_service(auth_client, token: str) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Serviço {uuid4().hex[:6]}",
            "duration_minutes": 60,
            "buffer_minutes": 10,
            "price": "120.00",
            "cost": "20.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_client(
    auth_client,
    token: str,
    *,
    phone: str | None = None,
) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {suffix}",
            "phone": phone or _phone(),
            "email": f"cliente-{suffix}@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_plan(
    auth_client,
    token: str,
    service_id: object,
    *,
    uses_per_cycle: int = 4,
    min_interval_days: int | None = None,
    allowed_weekdays: list[int] | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "service_id": service_id,
        "uses_per_cycle": uses_per_cycle,
    }
    if min_interval_days is not None:
        item["min_interval_days"] = min_interval_days
    if allowed_weekdays is not None:
        item["allowed_weekdays"] = allowed_weekdays
    response = await auth_client.post(
        PLANS,
        headers=_auth(token),
        json={
            "name": f"Clube {uuid4().hex[:6]}",
            "description": "Plano de teste",
            "price": "199.90",
            "billing_cycle": "MONTHLY",
            "items": [item],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _magic_link(auth_client, slug: str, phone: str) -> str:
    response = await auth_client.post(
        f"/api/v1/public/{slug}/magic-link",
        headers=_internal(),
        json={"phone": phone},
    )
    assert response.status_code == 200, response.text
    return parse_qs(urlparse(response.json()["url"]).query)["t"][0]


async def test_manager_contracts_plan_and_reads_quota(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(auth_client, token, service["id"], uses_per_cycle=4)
    client = await _create_client(auth_client, token)

    created = await auth_client.post(
        f"{CLIENTS}/{client['id']}/subscriptions",
        headers=_auth(token),
        json={"plan_id": plan["id"]},
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["client_id"] == client["id"]
    assert body["plan_id"] == plan["id"]
    assert body["status"] == "ACTIVE"
    assert body["quotas"][0]["uses_per_cycle"] == 4
    assert body["quotas"][0]["used"] == 0
    assert body["quotas"][0]["remaining"] == 4
    assert body["quotas"][0]["service_id"] == service["id"]

    listed = await auth_client.get(SUBSCRIPTIONS, headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    by_client = await auth_client.get(
        f"{CLIENTS}/{client['id']}/subscriptions",
        headers=_auth(token),
    )
    assert by_client.status_code == 200
    assert len(by_client.json()) == 1

    cancelled = await auth_client.post(
        f"{SUBSCRIPTIONS}/{body['id']}/cancel",
        headers=_auth(token),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    again = await auth_client.post(
        f"{SUBSCRIPTIONS}/{body['id']}/cancel",
        headers=_auth(token),
    )
    assert again.status_code == 409


async def test_public_contracts_plan_and_context_shows_quota(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(auth_client, token, service["id"], uses_per_cycle=2)
    phone = _phone()
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)

    context_before = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/context",
        params={"t": magic},
    )
    assert context_before.status_code == 200
    assert context_before.json()["client_name"] is None
    assert context_before.json()["subscription"] is None
    assert [item["id"] for item in context_before.json()["plans"]] == [
        plan["id"]
    ]
    assert context_before.json()["plans"][0]["items"][0]["service_name"]

    contracted = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/subscriptions",
        params={"t": magic},
        json={"plan_id": plan["id"], "full_name": "Cliente Novo Plano"},
    )

    assert contracted.status_code == 201, contracted.text
    body = contracted.json()
    assert body["status"] == "ACTIVE"
    assert body["plan_id"] == plan["id"]
    assert body["quotas"][0]["remaining"] == 2

    context_after = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/context",
        params={"t": magic},
    )
    assert context_after.status_code == 200
    data = context_after.json()
    assert data["client_name"] == "Cliente Novo Plano"
    assert data["subscription"]["plan_id"] == plan["id"]
    assert data["subscription"]["quotas"][0]["uses_per_cycle"] == 2


async def test_public_subscription_requires_name_for_new_client(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(auth_client, token, service["id"])
    magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    response = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/subscriptions",
        params={"t": magic},
        json={"plan_id": plan["id"]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Informe seu nome"


async def test_public_subscription_conflicts_for_same_active_plan(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(auth_client, token, service["id"])
    magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    first = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/subscriptions",
        params={"t": magic},
        json={"plan_id": plan["id"], "full_name": "Cliente Plano"},
    )
    assert first.status_code == 201, first.text

    second = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/subscriptions",
        params={"t": magic},
        json={"plan_id": plan["id"], "full_name": "Cliente Plano"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "Você já possui este plano ativo."


async def test_collaborator_cannot_list_subscriptions(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, collaborator)

    response = await auth_client.get(SUBSCRIPTIONS, headers=_auth(token))

    assert response.status_code == 403


async def test_subscriptions_are_isolated_between_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(auth_client, token, service["id"])
    client = await _create_client(auth_client, token)
    created = await auth_client.post(
        f"{CLIENTS}/{client['id']}/subscriptions",
        headers=_auth(token),
        json={"plan_id": plan["id"]},
    )
    assert created.status_code == 201, created.text

    other_token = await _login(auth_client, auth_user)
    listed = await auth_client.get(
        SUBSCRIPTIONS,
        headers=_auth(other_token),
    )
    assert listed.status_code == 200
    assert listed.json() == []

    cross = await auth_client.get(
        f"{CLIENTS}/{client['id']}/subscriptions",
        headers=_auth(other_token),
    )
    assert cross.status_code == 404
