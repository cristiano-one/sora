"""Console master: senha master, perfis de negócio e bloqueio clínico."""

from uuid import uuid4

import pytest
from app.core.config import settings
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

SYSTEM_LOGIN = "/api/v1/system/login"
SYSTEM_TENANTS = "/api/v1/system/tenants"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
CLIENTS = "/api/v1/clients"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _system(token: str) -> dict[str, str]:
    return {"X-System-Token": token}


async def _tenant_login(auth_client, user) -> str:
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


async def _system_token(auth_client, password: str = "master-test-123"):
    response = await auth_client.post(
        SYSTEM_LOGIN,
        json={"password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


async def test_system_admin_requires_master_password(
    auth_client,
    tenant_users,
    database_urls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "system_admin_password", "master-test-123")
    monkeypatch.setattr(
        settings,
        "migration_database_url",
        database_urls["owner"],
    )

    wrong = await auth_client.post(
        SYSTEM_LOGIN,
        json={"password": "senha-errada"},
    )
    assert wrong.status_code == 401

    token = await _system_token(auth_client)
    no_header = await auth_client.get(SYSTEM_TENANTS)
    assert no_header.status_code == 401

    listed = await auth_client.get(
        SYSTEM_TENANTS,
        headers=_system(token),
    )
    assert listed.status_code == 200
    assert any(
        item["id"] == str(tenant_users.tenant_id) for item in listed.json()
    )

    logout = await auth_client.post(
        "/api/v1/system/logout",
        headers=_system(token),
    )
    assert logout.status_code == 204

    expired = await auth_client.get(
        SYSTEM_TENANTS,
        headers=_system(token),
    )
    assert expired.status_code == 401


async def test_profile_controls_medical_records(
    auth_client,
    tenant_users,
    database_urls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "system_admin_password", "master-test-123")
    monkeypatch.setattr(
        settings,
        "migration_database_url",
        database_urls["owner"],
    )
    system_token = await _system_token(auth_client)
    owner = tenant_users.users[UserRole.OWNER]
    owner_token = await _tenant_login(auth_client, owner)

    me = await auth_client.get(ME, headers=_auth(owner_token))
    assert me.status_code == 200
    assert me.json()["business_profile"] == "AESTHETICS"

    changed = await auth_client.patch(
        f"{SYSTEM_TENANTS}/{tenant_users.tenant_id}/profile",
        headers=_system(system_token),
        json={"business_profile": "SALON"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["business_profile"] == "SALON"

    me_salon = await auth_client.get(ME, headers=_auth(owner_token))
    assert me_salon.json()["business_profile"] == "SALON"

    client = await auth_client.post(
        CLIENTS,
        headers=_auth(owner_token),
        json={
            "full_name": f"Cliente Salão {uuid4().hex[:5]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert client.status_code == 201
    client_id = client.json()["id"]

    blocked = await auth_client.post(
        f"{CLIENTS}/{client_id}/records",
        headers=_auth(owner_token),
        json={"title": "Anamnese", "notes": "Teste"},
    )
    assert blocked.status_code == 403

    listing = await auth_client.get(
        f"{CLIENTS}/{client_id}/records",
        headers=_auth(owner_token),
    )
    assert listing.status_code == 200
    assert listing.json() == []

    back = await auth_client.patch(
        f"{SYSTEM_TENANTS}/{tenant_users.tenant_id}/profile",
        headers=_system(system_token),
        json={"business_profile": "AESTHETICS"},
    )
    assert back.status_code == 200

    allowed = await auth_client.post(
        f"{CLIENTS}/{client_id}/records",
        headers=_auth(owner_token),
        json={"title": "Anamnese", "notes": "Teste"},
    )
    assert allowed.status_code == 201, allowed.text


async def test_system_admin_is_disabled_without_password(
    auth_client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "system_admin_password", "")
    response = await auth_client.post(
        SYSTEM_LOGIN,
        json={"password": "qualquer"},
    )
    assert response.status_code == 503
