"""Testes de RBAC em 3 níveis e sessão com RLS por requisição."""

import pytest
from app.db.session import create_engine, create_session_factory
from app.models import Tenant, UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TENANT_CURRENT = "/api/v1/tenants/current"
ME = "/api/v1/auth/me"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(auth_client, user) -> str:
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": user.tenant_slug,
            "email": user.email,
            "password": user.password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_owner_can_read_current_tenant(auth_client, tenant_users) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    response = await auth_client.get(TENANT_CURRENT, headers=_auth(token))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(tenant_users.tenant_id)
    assert data["name"] == tenant_users.tenant_name
    assert data["slug"] == tenant_users.tenant_slug


async def test_admin_can_read_current_tenant(auth_client, tenant_users) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.ADMIN])

    response = await auth_client.get(TENANT_CURRENT, headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["id"] == str(tenant_users.tenant_id)


async def test_collaborator_cannot_read_current_tenant(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.COLLABORATOR])

    response = await auth_client.get(TENANT_CURRENT, headers=_auth(token))

    assert response.status_code == 403
    assert response.json() == {"detail": "Acesso negado"}


async def test_collaborator_can_read_own_profile(auth_client, tenant_users) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.COLLABORATOR])

    response = await auth_client.get(ME, headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["role"] == UserRole.COLLABORATOR.value


async def test_unauthenticated_cannot_read_current_tenant(auth_client) -> None:
    response = await auth_client.get(TENANT_CURRENT)

    assert response.status_code == 401


async def test_tenant_session_is_scoped_by_rls(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    other_slug = f"outra-rbac-{tenant_users.tenant_slug[-8:]}"
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(Tenant(name="Outra Clínica", slug=other_slug))
        await session.commit()
    await engine.dispose()

    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    response = await auth_client.get(TENANT_CURRENT, headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["id"] == str(tenant_users.tenant_id)
