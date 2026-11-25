"""Testes de colaboradores, comissões e revogação ao desativar."""

from decimal import Decimal
from uuid import uuid4

import pytest
from app.models import CommissionBase, UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

USERS = "/api/v1/users"
ME_COMMISSION = "/api/v1/users/me/commission"
ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"


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


def _new_user_payload(suffix: str, *, role: str = "COLLABORATOR") -> dict[str, object]:
    return {
        "full_name": f"Colaborador {suffix}",
        "email": f"colab-{suffix}@example.com",
        "password": "senha-forte-123",
        "role": role,
        "commission_percentage": "40.00",
        "commission_fixed": "5.00",
        "commission_base": "GROSS",
    }


async def test_owner_can_create_collaborator(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    suffix = uuid4().hex[:8]

    response = await auth_client.post(
        USERS,
        headers=_auth(owner_token),
        json=_new_user_payload(suffix),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == f"colab-{suffix}@example.com"
    assert data["role"] == UserRole.COLLABORATOR.value
    assert data["commission_base"] == CommissionBase.GROSS.value
    assert "hashed_password" not in data
    assert "password" not in data


async def test_admin_can_create_collaborator(auth_client, tenant_users) -> None:
    admin_token = await _login(auth_client, tenant_users.users[UserRole.ADMIN])
    suffix = uuid4().hex[:8]

    response = await auth_client.post(
        USERS,
        headers=_auth(admin_token),
        json=_new_user_payload(suffix),
    )

    assert response.status_code == 201


async def test_admin_cannot_create_admin(auth_client, tenant_users) -> None:
    admin_token = await _login(auth_client, tenant_users.users[UserRole.ADMIN])
    suffix = uuid4().hex[:8]

    response = await auth_client.post(
        USERS,
        headers=_auth(admin_token),
        json=_new_user_payload(suffix, role="ADMIN"),
    )

    assert response.status_code == 403


async def test_cannot_create_owner(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    suffix = uuid4().hex[:8]

    response = await auth_client.post(
        USERS,
        headers=_auth(owner_token),
        json=_new_user_payload(suffix, role="OWNER"),
    )

    assert response.status_code == 403


async def test_collaborator_cannot_list_users(auth_client, tenant_users) -> None:
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    response = await auth_client.get(USERS, headers=_auth(collab_token))

    assert response.status_code == 403


async def test_collaborator_reads_only_own_commission(
    auth_client,
    tenant_users,
) -> None:
    collab = tenant_users.users[UserRole.COLLABORATOR]
    collab_token = await _login(auth_client, collab)

    response = await auth_client.get(ME_COMMISSION, headers=_auth(collab_token))

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(collab.user_id)
    assert data["commission_base"] == CommissionBase.GROSS.value
    assert Decimal(str(data["commission_percentage"])) == Decimal("40.00")
    assert Decimal(str(data["commission_fixed"])) == Decimal("5.00")


async def test_owner_can_update_commission(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    collab = tenant_users.users[UserRole.COLLABORATOR]

    response = await auth_client.patch(
        f"{USERS}/{collab.user_id}",
        headers=_auth(owner_token),
        json={"commission_percentage": "35.50"},
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["commission_percentage"])) == Decimal("35.50")
    assert data["role"] == UserRole.COLLABORATOR.value


async def test_admin_cannot_modify_owner(auth_client, tenant_users) -> None:
    admin_token = await _login(auth_client, tenant_users.users[UserRole.ADMIN])
    owner = tenant_users.users[UserRole.OWNER]

    response = await auth_client.patch(
        f"{USERS}/{owner.user_id}",
        headers=_auth(admin_token),
        json={"full_name": "Hack"},
    )

    assert response.status_code == 403


async def test_cross_tenant_patch_returns_404(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    suffix = uuid4().hex[:8]

    signup = await auth_client.post(
        "/api/v1/tenants",
        json={
            "name": "Outra Clínica",
            "slug": f"outra-{suffix}",
            "tax_regime": "COMPLETE",
            "owner_full_name": "Outro Owner",
            "owner_email": f"outro-{suffix}@example.com",
            "owner_password": "senha-forte-123",
        },
    )
    assert signup.status_code == 201
    other_owner_id = signup.json()["owner"]["id"]

    response = await auth_client.patch(
        f"{USERS}/{other_owner_id}",
        headers=_auth(owner_token),
        json={"full_name": "Invasor"},
    )

    assert response.status_code == 404


async def test_deactivate_user_revokes_sessions(auth_client, tenant_users) -> None:
    collab = tenant_users.users[UserRole.COLLABORATOR]
    collab_token = await _login(auth_client, collab)
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    deactivated = await auth_client.patch(
        f"{USERS}/{collab.user_id}",
        headers=_auth(owner_token),
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    me = await auth_client.get(ME, headers=_auth(collab_token))
    assert me.status_code == 401
