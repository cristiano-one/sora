"""Worker de créditos de aniversário percorrendo todos os tenants."""

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import settings
from app.models import UserRole
from app.workers.birthday_credits import run_all

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime.now(TZ).date()
LOGIN = "/api/v1/auth/login"
CLIENTS = "/api/v1/clients"
SETTINGS = "/api/v1/tenants/settings"
CREDITS = "/api/v1/ai/birthday-credits"


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


async def test_worker_creates_credits_for_all_tenants(
    auth_client,
    tenant_users,
    database_urls,
    monkeypatch,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    settings_response = await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={"birthday_credit_amount": "20.00"},
    )
    assert settings_response.status_code == 200
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Aniversariante Worker {uuid4().hex[:6]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
            "birth_date": (TODAY + timedelta(days=1))
            .replace(year=1990)
            .isoformat(),
        },
    )
    assert client.status_code == 201, client.text

    monkeypatch.setattr(
        settings,
        "migration_database_url",
        database_urls["owner"],
    )
    monkeypatch.setattr(
        settings,
        "database_url",
        database_urls["app"],
    )

    result = await run_all()

    assert result.errors == 0
    assert result.tenants >= 1
    assert result.created >= 1

    credits = await auth_client.get(
        CREDITS,
        headers=_auth(token),
        params={"year": str(TODAY.year)},
    )
    assert credits.status_code == 200
    assert any(
        item["client_id"] == client.json()["id"]
        for item in credits.json()
    )
