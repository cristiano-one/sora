"""Testes de autenticação, rotação e revogação de sessão (Zero-Leak)."""

import pytest
from app.core.config import settings
from app.db.session import create_engine, create_session_factory
from app.models import Tenant
from sqlalchemy import text

pytestmark = [pytest.mark.security, pytest.mark.integration]

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def _login_payload(auth_user) -> dict[str, str]:
    return {
        "tenant_slug": auth_user.tenant_slug,
        "email": auth_user.email,
        "password": auth_user.password,
    }


async def _login(auth_client, auth_user) -> dict[str, str]:
    response = await auth_client.post(LOGIN, json=_login_payload(auth_user))
    assert response.status_code == 200
    return response.json()


async def test_login_returns_token_pair(auth_client, auth_user, test_redis) -> None:
    response = await auth_client.post(LOGIN, json=_login_payload(auth_user))

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.jwt_access_token_expire_minutes * 60
    assert data["access_token"]
    assert data["refresh_token"]

    keys = await test_redis.keys("*")
    assert keys
    assert all(key.startswith(f"tenant:{auth_user.tenant_id}:") for key in keys)


async def test_login_response_has_only_public_fields(auth_client, auth_user) -> None:
    tokens = await _login(auth_client, auth_user)

    assert set(tokens) == {"access_token", "refresh_token", "token_type", "expires_in"}


async def test_login_with_wrong_password_returns_generic_401(
    auth_client,
    auth_user,
) -> None:
    payload = _login_payload(auth_user) | {"password": "senha-errada"}
    response = await auth_client.post(LOGIN, json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}


async def test_login_with_unknown_tenant_returns_generic_401(
    auth_client,
    auth_user,
) -> None:
    payload = _login_payload(auth_user) | {"tenant_slug": "tenant-inexistente"}
    response = await auth_client.post(LOGIN, json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}


async def test_login_does_not_cross_tenant(
    auth_client,
    auth_user,
    database_urls,
) -> None:
    other_slug = f"outra-clinica-{auth_user.tenant_slug[-8:]}"
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(Tenant(name="Outra Clínica", slug=other_slug))
        await session.commit()
    await engine.dispose()

    payload = _login_payload(auth_user) | {"tenant_slug": other_slug}
    response = await auth_client.post(LOGIN, json=payload)

    assert response.status_code == 401


async def test_me_returns_current_user(auth_client, auth_user) -> None:
    tokens = await _login(auth_client, auth_user)

    response = await auth_client.get(
        ME,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(auth_user.user_id)
    assert data["tenant_id"] == str(auth_user.tenant_id)
    assert data["email"] == auth_user.email
    assert data["role"] == auth_user.role.value


async def test_me_without_token_returns_401(auth_client) -> None:
    response = await auth_client.get(ME)

    assert response.status_code == 401


async def test_logout_revokes_access_and_refresh(auth_client, auth_user) -> None:
    tokens = await _login(auth_client, auth_user)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await auth_client.post(
        LOGOUT,
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 204

    me = await auth_client.get(ME, headers=headers)
    assert me.status_code == 401

    refresh = await auth_client.post(
        REFRESH,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401


async def test_refresh_rotates_and_rejects_reuse(auth_client, auth_user) -> None:
    tokens = await _login(auth_client, auth_user)

    refreshed = await auth_client.post(
        REFRESH,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reuse = await auth_client.post(
        REFRESH,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse.status_code == 401

    # O reuso revoga todas as sessões, inclusive o par recém-emitido.
    me = await auth_client.get(
        ME,
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me.status_code == 401

    refresh_new = await auth_client.post(
        REFRESH,
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert refresh_new.status_code == 401


async def test_refresh_with_invalid_token_returns_401(auth_client) -> None:
    response = await auth_client.post(REFRESH, json={"refresh_token": "invalido"})

    assert response.status_code == 401


async def test_disabled_user_cannot_login(
    auth_client,
    auth_user,
    database_urls,
) -> None:
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        await session.execute(
            text("UPDATE users SET is_active = false WHERE id = :user_id"),
            {"user_id": auth_user.user_id},
        )
        await session.commit()
    await engine.dispose()

    response = await auth_client.post(LOGIN, json=_login_payload(auth_user))

    assert response.status_code == 401
