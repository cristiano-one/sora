"""Testes do catálogo: serviços, pacotes e planos de assinatura."""

from decimal import Decimal
from uuid import uuid4

import pytest
from app.models import BillingCycle, UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

SERVICES = "/api/v1/services"
PACKAGES = "/api/v1/packages"
PLANS = "/api/v1/subscription-plans"
LOGIN = "/api/v1/auth/login"
TENANTS = "/api/v1/tenants"


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


def _service_payload(name: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "description": "Serviço de teste",
        "duration_minutes": 60,
        "buffer_minutes": 10,
        "price": "150.00",
        "cost": "20.00",
        "requires_deposit": True,
        "deposit_amount": "30.00",
        "show_average_price": True,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


async def _create_service(auth_client, token: str, name: str) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json=_service_payload(name),
    )
    assert response.status_code == 201
    return response.json()


async def test_owner_creates_service(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    response = await auth_client.post(
        SERVICES,
        headers=_auth(owner_token),
        json=_service_payload("Corte"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Corte"
    assert data["duration_minutes"] == 60
    assert data["buffer_minutes"] == 10
    assert Decimal(str(data["price"])) == Decimal("150.00")
    assert Decimal(str(data["cost"])) == Decimal("20.00")
    assert data["requires_deposit"] is True
    assert Decimal(str(data["deposit_amount"])) == Decimal("30.00")
    assert data["show_average_price"] is True


async def test_admin_creates_service(auth_client, tenant_users) -> None:
    admin_token = await _login(auth_client, tenant_users.users[UserRole.ADMIN])

    response = await auth_client.post(
        SERVICES,
        headers=_auth(admin_token),
        json=_service_payload("Barba"),
    )

    assert response.status_code == 201


async def test_collaborator_can_list_but_not_create(
    auth_client,
    tenant_users,
) -> None:
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    listing = await auth_client.get(SERVICES, headers=_auth(collab_token))
    creation = await auth_client.post(
        SERVICES,
        headers=_auth(collab_token),
        json=_service_payload("Proibido"),
    )

    assert listing.status_code == 200
    assert creation.status_code == 403


async def test_service_deposit_is_required_when_enabled(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    payload = _service_payload("Sinal", requires_deposit=True, deposit_amount=None)

    response = await auth_client.post(
        SERVICES,
        headers=_auth(owner_token),
        json=payload,
    )

    assert response.status_code == 422


async def test_service_duration_validation(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    payload = _service_payload("Curto", duration_minutes=1)

    response = await auth_client.post(
        SERVICES,
        headers=_auth(owner_token),
        json=payload,
    )

    assert response.status_code == 422


async def test_update_service_toggles_average_price(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    service = await _create_service(auth_client, owner_token, "Coloração")

    response = await auth_client.patch(
        f"{SERVICES}/{service['id']}",
        headers=_auth(owner_token),
        json={"show_average_price": False, "price": "180.00"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["show_average_price"] is False
    assert Decimal(str(data["price"])) == Decimal("180.00")


async def test_create_package_with_items(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    service = await _create_service(auth_client, owner_token, "Escova")

    response = await auth_client.post(
        PACKAGES,
        headers=_auth(owner_token),
        json={
            "name": "Pacote Escova",
            "description": "4 escovas",
            "total_price": "400.00",
            "items": [{"service_id": service["id"], "quantity": 4}],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["total_price"])) == Decimal("400.00")
    assert len(data["items"]) == 1
    assert data["items"][0]["service_id"] == service["id"]
    assert data["items"][0]["quantity"] == 4

    listing = await auth_client.get(PACKAGES, headers=_auth(owner_token))
    assert listing.status_code == 200
    assert listing.json()[0]["name"] == "Pacote Escova"


async def test_package_with_unknown_service_returns_404(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    response = await auth_client.post(
        PACKAGES,
        headers=_auth(owner_token),
        json={
            "name": "Pacote Fantasma",
            "total_price": "100.00",
            "items": [{"service_id": str(uuid4()), "quantity": 1}],
        },
    )

    assert response.status_code == 404


async def test_create_subscription_plan(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    service = await _create_service(auth_client, owner_token, "Limpeza")

    response = await auth_client.post(
        PLANS,
        headers=_auth(owner_token),
        json={
            "name": "Clube Limpeza",
            "description": "4 limpezas por mês",
            "price": "199.90",
            "billing_cycle": "MONTHLY",
            "items": [
                {
                    "service_id": service["id"],
                    "uses_per_cycle": 4,
                    "min_interval_days": 7,
                    "allowed_weekdays": [1, 2, 3, 4],
                }
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["billing_cycle"] == BillingCycle.MONTHLY.value
    assert Decimal(str(data["price"])) == Decimal("199.90")
    assert len(data["items"]) == 1
    assert data["items"][0]["uses_per_cycle"] == 4
    assert data["items"][0]["min_interval_days"] == 7
    assert data["items"][0]["allowed_weekdays"] == [1, 2, 3, 4]

    listing = await auth_client.get(PLANS, headers=_auth(owner_token))
    assert listing.status_code == 200
    assert listing.json()[0]["name"] == "Clube Limpeza"


async def test_plan_invalid_weekday_returns_422(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    response = await auth_client.post(
        PLANS,
        headers=_auth(owner_token),
        json={
            "name": "Plano Inválido",
            "price": "100.00",
            "billing_cycle": "MONTHLY",
            "items": [
                {
                    "service_id": str(uuid4()),
                    "uses_per_cycle": 1,
                    "allowed_weekdays": [7],
                }
            ],
        },
    )

    assert response.status_code == 422


async def test_collaborator_cannot_create_package_or_plan(
    auth_client,
    tenant_users,
) -> None:
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    package = await auth_client.post(
        PACKAGES,
        headers=_auth(collab_token),
        json={
            "name": "Pacote Proibido",
            "total_price": "10.00",
            "items": [{"service_id": str(uuid4()), "quantity": 1}],
        },
    )
    plan = await auth_client.post(
        PLANS,
        headers=_auth(collab_token),
        json={
            "name": "Plano Proibido",
            "price": "10.00",
            "billing_cycle": "MONTHLY",
            "items": [{"service_id": str(uuid4()), "uses_per_cycle": 1}],
        },
    )

    assert package.status_code == 403
    assert plan.status_code == 403


async def test_catalog_is_isolated_between_tenants(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    service = await _create_service(auth_client, owner_token, "Exclusivo A")

    suffix = uuid4().hex[:8]
    signup = await auth_client.post(
        TENANTS,
        json={
            "name": "Clínica B",
            "slug": f"clinica-b-{suffix}",
            "tax_regime": "COMPLETE",
            "owner_full_name": "Owner B",
            "owner_email": f"owner-b-{suffix}@example.com",
            "owner_password": "senha-forte-123",
        },
    )
    assert signup.status_code == 201

    login_b = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": f"clinica-b-{suffix}",
            "email": f"owner-b-{suffix}@example.com",
            "password": "senha-forte-123",
        },
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]

    listing = await auth_client.get(SERVICES, headers=_auth(token_b))

    assert listing.status_code == 200
    assert all(item["id"] != service["id"] for item in listing.json())

    patch = await auth_client.patch(
        f"{SERVICES}/{service['id']}",
        headers=_auth(token_b),
        json={"name": "Invasão"},
    )
    assert patch.status_code == 404
