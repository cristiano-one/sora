"""Recuperação de senha e convite de colaborador por e-mail."""

from uuid import uuid4

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
ACCEPT = "/api/v1/auth/accept-invite"
USERS = "/api/v1/users"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(auth_client, *, slug: str, email: str, password: str):
    return await auth_client.post(
        LOGIN,
        json={"tenant_slug": slug, "email": email, "password": password},
    )


async def _owner_token(auth_client, tenant_users) -> str:
    owner = tenant_users.users[UserRole.OWNER]
    response = await _login(
        auth_client,
        slug=tenant_users.tenant_slug,
        email=owner.email,
        password=owner.password,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_forgot_password_resets_and_revokes_old_password(
    auth_client,
    tenant_users,
    test_redis,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    requested = await auth_client.post(
        FORGOT,
        json={"tenant_slug": tenant_users.tenant_slug, "email": owner.email},
    )
    assert requested.status_code == 202
    assert "Se o e-mail existir" in requested.json()["message"]

    keys = await test_redis.keys(
        f"tenant:{tenant_users.tenant_id}:auth:password_reset:*"
    )
    assert len(keys) == 1
    token = keys[0].rsplit(":", 1)[-1]

    reset = await auth_client.post(
        RESET,
        json={
            "tenant_slug": tenant_users.tenant_slug,
            "token": token,
            "new_password": "nova-senha-123",
        },
    )
    assert reset.status_code == 204, reset.text

    old = await _login(
        auth_client,
        slug=tenant_users.tenant_slug,
        email=owner.email,
        password=owner.password,
    )
    assert old.status_code == 401

    new = await _login(
        auth_client,
        slug=tenant_users.tenant_slug,
        email=owner.email,
        password="nova-senha-123",
    )
    assert new.status_code == 200

    reused = await auth_client.post(
        RESET,
        json={
            "tenant_slug": tenant_users.tenant_slug,
            "token": token,
            "new_password": "outra-senha-123",
        },
    )
    assert reused.status_code == 400

    unknown = await auth_client.post(
        FORGOT,
        json={
            "tenant_slug": tenant_users.tenant_slug,
            "email": f"nao-existe-{uuid4().hex[:6]}@example.com",
        },
    )
    assert unknown.status_code == 202


async def test_invite_creates_user_with_initial_password(
    auth_client,
    tenant_users,
    test_redis,
) -> None:
    token = await _owner_token(auth_client, tenant_users)
    email = f"convidado-{uuid4().hex[:8]}@example.com"
    invited = await auth_client.post(
        f"{USERS}/invite",
        headers=_auth(token),
        json={
            "full_name": "Convidado Teste",
            "email": email,
            "role": "COLLABORATOR",
            "commission_percentage": "35.00",
            "commission_base": "GROSS",
        },
    )
    assert invited.status_code == 201, invited.text

    keys = await test_redis.keys(
        f"tenant:{tenant_users.tenant_id}:auth:invite:*"
    )
    assert len(keys) == 1
    invite_token = keys[0].rsplit(":", 1)[-1]

    accepted = await auth_client.post(
        ACCEPT,
        json={
            "tenant_slug": tenant_users.tenant_slug,
            "token": invite_token,
            "new_password": "convite-123",
        },
    )
    assert accepted.status_code == 204, accepted.text

    login = await _login(
        auth_client,
        slug=tenant_users.tenant_slug,
        email=email,
        password="convite-123",
    )
    assert login.status_code == 200

    collaborator_token = await _login(
        auth_client,
        slug=tenant_users.tenant_slug,
        email=tenant_users.users[UserRole.COLLABORATOR].email,
        password=tenant_users.users[UserRole.COLLABORATOR].password,
    )
    forbidden = await auth_client.post(
        f"{USERS}/invite",
        headers=_auth(collaborator_token.json()["access_token"]),
        json={
            "full_name": "Sem Permissão",
            "email": f"negado-{uuid4().hex[:8]}@example.com",
            "role": "COLLABORATOR",
        },
    )
    assert forbidden.status_code == 403
