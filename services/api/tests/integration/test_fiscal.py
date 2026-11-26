"""Fiscal mock (NFS-e) e vínculo parceiro/MEI."""

from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"
SALES = "/api/v1/sales"
ACCOUNTS = "/api/v1/finance/accounts"
SETTINGS = "/api/v1/tenants/settings"
USERS = "/api/v1/users"


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


async def _paid_sale(auth_client, token: str, collaborator_id) -> dict:
    account = await auth_client.post(
        ACCOUNTS,
        headers=_auth(token),
        json={
            "name": f"Caixa Fiscal {uuid4().hex[:5]}",
            "type": "CASH",
            "initial_balance": "0.00",
        },
    )
    assert account.status_code == 201
    suffix = uuid4().hex[:5]
    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Fiscal {suffix}",
            "duration_minutes": 30,
            "buffer_minutes": 0,
            "price": "90.00",
            "cost": "10.00",
        },
    )
    assert service.status_code == 201
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": "Cliente Fiscal",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert client.status_code == 201
    appointment = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client.json()["id"],
            "service_id": service.json()["id"],
            "collaborator_id": str(collaborator_id),
            "starts_at": datetime.combine(DAY, time(15), tzinfo=TZ).isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text
    sale = await auth_client.post(
        f"{SALES}/from-appointment/{appointment.json()['id']}",
        headers=_auth(token),
    )
    assert sale.status_code == 200, sale.text
    closed = await auth_client.post(
        f"{SALES}/{sale.json()['id']}/close",
        headers=_auth(token),
        json={
            "payment_method": "CARD",
            "account_id": account.json()["id"],
        },
    )
    assert closed.status_code == 200, closed.text
    return closed.json()


async def test_nfse_mock_issue_get_and_cancel(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    settings = await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={
            "fiscal_enabled": True,
            "fiscal_provider": "mock",
            "fiscal_municipality": "São Paulo",
            "fiscal_service_code": "14.01",
            "fiscal_email": "fiscal@example.com",
        },
    )
    assert settings.status_code == 200, settings.text
    sale = await _paid_sale(auth_client, token, collaborator.user_id)

    invoice = await auth_client.post(
        f"{SALES}/{sale['id']}/invoice",
        headers=_auth(token),
    )
    assert invoice.status_code == 201, invoice.text
    data = invoice.json()
    assert data["status"] == "ISSUED"
    assert data["number"].startswith("MOCK-")
    assert data["amount"] == "90.00"

    fetched = await auth_client.get(
        f"{SALES}/{sale['id']}/invoice",
        headers=_auth(token),
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == data["id"]

    cancelled = await auth_client.post(
        f"{SALES}/{sale['id']}/invoice/cancel",
        headers=_auth(token),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    again = await auth_client.post(
        f"{SALES}/{sale['id']}/invoice",
        headers=_auth(token),
    )
    assert again.status_code == 422


async def test_fiscal_requires_flag_and_user_employment_type(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    sale = await _paid_sale(auth_client, token, collaborator.user_id)

    disabled = await auth_client.post(
        f"{SALES}/{sale['id']}/invoice",
        headers=_auth(token),
    )
    assert disabled.status_code == 422

    suffix = uuid4().hex[:6]
    created = await auth_client.post(
        USERS,
        headers=_auth(token),
        json={
            "full_name": "Parceiro Teste",
            "email": f"parceiro-{suffix}@example.com",
            "password": "senha-forte-123",
            "role": "COLLABORATOR",
            "employment_type": "PARTNER",
            "commission_percentage": "40.00",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["employment_type"] == "PARTNER"

    updated = await auth_client.patch(
        f"{USERS}/{created.json()['id']}",
        headers=_auth(token),
        json={"employment_type": "MEI"},
    )
    assert updated.status_code == 200
    assert updated.json()["employment_type"] == "MEI"
