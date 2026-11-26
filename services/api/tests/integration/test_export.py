"""Exportação LGPD: dono, conteúdo e isolamento multi-tenant."""

from uuid import uuid4

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
CLIENTS = "/api/v1/clients"
EXPORT = "/api/v1/tenants/export"


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


async def test_owner_exports_all_tenant_data(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Exportável {uuid4().hex[:6]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert client.status_code == 201, client.text

    response = await auth_client.get(EXPORT, headers=_auth(token))

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["tenant"]["slug"] == tenant_users.tenant_slug
    assert any(
        item["full_name"] == client.json()["full_name"]
        for item in data["clients"]
    )
    raw = response.text
    assert "hashed_password" not in raw
    assert "password" not in raw
    assert "score" in data["clients"][0]


async def test_export_is_owner_only(
    auth_client,
    tenant_users,
) -> None:
    for role in (UserRole.ADMIN, UserRole.COLLABORATOR):
        token = await _login(auth_client, tenant_users.users[role])
        response = await auth_client.get(EXPORT, headers=_auth(token))
        assert response.status_code == 403


async def test_export_does_not_cross_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente Tenant A {uuid4().hex[:6]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert client.status_code == 201

    other_token = await _login(auth_client, auth_user)
    other = await auth_client.get(EXPORT, headers=_auth(other_token))

    assert other.status_code == 200
    data = other.json()
    assert data["tenant"]["slug"] == auth_user.tenant_slug
    assert all(
        item["full_name"] != client.json()["full_name"]
        for item in data["clients"]
    )
