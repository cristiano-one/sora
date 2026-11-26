"""Testes do cadastro de empresa (tenant + OWNER) e isolamento RLS."""

from uuid import uuid4

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TENANTS = "/api/v1/tenants"
TENANT_CURRENT = "/api/v1/tenants/current"
LOGIN = "/api/v1/auth/login"


def _payload(
    suffix: str,
    *,
    tax_regime: str = "COMPLETE",
    business_profile: str = "AESTHETICS",
) -> dict[str, str]:
    return {
        "name": f"Clínica {suffix}",
        "slug": f"clinica-{suffix}",
        "tax_regime": tax_regime,
        "business_profile": business_profile,
        "owner_full_name": f"Owner {suffix}",
        "owner_email": f"owner-{suffix}@example.com",
        "owner_password": "senha-forte-123",
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(auth_client, payload: dict[str, str]) -> str:
    response = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": payload["slug"],
            "email": payload["owner_email"],
            "password": payload["owner_password"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_create_tenant_with_owner(auth_client) -> None:
    suffix = f"signup-{uuid4().hex[:8]}"
    payload = _payload(suffix)

    response = await auth_client.post(TENANTS, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == payload["slug"]
    assert data["tax_regime"] == "COMPLETE"
    assert data["business_profile"] == "AESTHETICS"
    assert data["owner"]["email"] == payload["owner_email"]
    assert data["owner"]["role"] == UserRole.OWNER.value
    assert "password" not in data["owner"]
    assert "hashed_password" not in data["owner"]

    token = await _login(auth_client, payload)
    current = await auth_client.get(TENANT_CURRENT, headers=_auth(token))

    assert current.status_code == 200
    assert current.json()["id"] == data["id"]
    assert current.json()["tax_regime"] == "COMPLETE"
    assert current.json()["business_profile"] == "AESTHETICS"


async def test_signup_can_choose_podology_profile(auth_client) -> None:
    suffix = f"pod-{uuid4().hex[:8]}"
    payload = _payload(suffix, business_profile="PODOLOGY")

    response = await auth_client.post(TENANTS, json=payload)

    assert response.status_code == 201
    assert response.json()["business_profile"] == "PODOLOGY"

    token = await _login(auth_client, payload)
    me = await auth_client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["business_profile"] == "PODOLOGY"


async def test_create_mei_tenant(auth_client) -> None:
    suffix = f"mei-{uuid4().hex[:8]}"
    payload = _payload(suffix, tax_regime="MEI")

    response = await auth_client.post(TENANTS, json=payload)

    assert response.status_code == 201
    assert response.json()["tax_regime"] == "MEI"


async def test_duplicate_slug_returns_409(auth_client) -> None:
    suffix = f"dup-{uuid4().hex[:8]}"
    payload = _payload(suffix)
    assert (await auth_client.post(TENANTS, json=payload)).status_code == 201

    second = payload | {
        "name": "Outra Clínica",
        "owner_email": f"outro-{suffix}@example.com",
    }
    response = await auth_client.post(TENANTS, json=second)

    assert response.status_code == 409
    assert response.json() == {"detail": "Slug indisponível"}


async def test_invalid_slug_returns_422(auth_client) -> None:
    payload = _payload(f"inv-{uuid4().hex[:8]}") | {"slug": "Clinica Com Espaço"}

    response = await auth_client.post(TENANTS, json=payload)

    assert response.status_code == 422


async def test_weak_password_returns_422(auth_client) -> None:
    payload = _payload(f"weak-{uuid4().hex[:8]}") | {"owner_password": "123"}

    response = await auth_client.post(TENANTS, json=payload)

    assert response.status_code == 422


async def test_new_tenants_are_isolated(auth_client) -> None:
    suffix_a = f"iso-a-{uuid4().hex[:8]}"
    suffix_b = f"iso-b-{uuid4().hex[:8]}"
    payload_a = _payload(suffix_a, tax_regime="MEI")
    payload_b = _payload(suffix_b, tax_regime="COMPLETE")

    created_a = await auth_client.post(TENANTS, json=payload_a)
    created_b = await auth_client.post(TENANTS, json=payload_b)
    assert created_a.status_code == 201
    assert created_b.status_code == 201

    token_a = await _login(auth_client, payload_a)
    token_b = await _login(auth_client, payload_b)

    current_a = await auth_client.get(TENANT_CURRENT, headers=_auth(token_a))
    current_b = await auth_client.get(TENANT_CURRENT, headers=_auth(token_b))

    assert current_a.status_code == 200
    assert current_b.status_code == 200
    assert current_a.json()["id"] == created_a.json()["id"]
    assert current_b.json()["id"] == created_b.json()["id"]
    assert current_a.json()["id"] != current_b.json()["id"]
    assert current_a.json()["tax_regime"] == "MEI"
    assert current_b.json()["tax_regime"] == "COMPLETE"
