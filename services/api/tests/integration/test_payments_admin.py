"""Painel admin de Pix: listagem, confirmação manual e isolamento."""

from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
APPT_DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"
PAYMENTS = "/api/v1/payments"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _at(hour: int = 9) -> datetime:
    return datetime.combine(APPT_DAY, time(hour), tzinfo=TZ)


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


async def _pending_payment(auth_client, token: str) -> dict:
    suffix = uuid4().hex[:6]
    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Sinal {suffix}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "120.00",
            "cost": "10.00",
            "requires_deposit": True,
            "deposit_amount": "30.00",
        },
    )
    assert service.status_code == 201, service.text
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente Pix {suffix}",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert client.status_code == 201, client.text
    appointment = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client.json()["id"],
            "service_id": service.json()["id"],
            "starts_at": _at().isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text
    assert appointment.json()["status"] == "PENDING_DEPOSIT"

    payments = await auth_client.get(
        PAYMENTS,
        headers=_auth(token),
        params={"status": "PENDING"},
    )
    assert payments.status_code == 200, payments.text
    payment = next(
        item
        for item in payments.json()
        if item["appointment_id"] == appointment.json()["id"]
    )
    return {"appointment": appointment.json(), "payment": payment}


async def test_manager_lists_and_confirms_pending_pix(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    data = await _pending_payment(auth_client, token)
    payment = data["payment"]
    assert payment["amount"] == "30.00"
    assert payment["client_name"].startswith("Cliente Pix")

    confirmed = await auth_client.post(
        f"{PAYMENTS}/{payment['id']}/confirm",
        headers=_auth(token),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "PAID"
    assert confirmed.json()["paid_at"] is not None

    appointment = await auth_client.get(
        f"{APPOINTMENTS}/{data['appointment']['id']}",
        headers=_auth(token),
    )
    assert appointment.status_code == 200
    assert appointment.json()["status"] == "CONFIRMED"

    again = await auth_client.post(
        f"{PAYMENTS}/{payment['id']}/confirm",
        headers=_auth(token),
    )
    assert again.status_code == 200
    assert again.json()["status"] == "PAID"


async def test_collaborator_cannot_access_payment_panel(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    response = await auth_client.get(PAYMENTS, headers=_auth(token))
    assert response.status_code == 403


async def test_payment_cannot_cross_tenant(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    data = await _pending_payment(auth_client, token)

    other_token = await _login(auth_client, auth_user)
    other_list = await auth_client.get(PAYMENTS, headers=_auth(other_token))
    assert other_list.status_code == 200
    assert all(
        item["id"] != data["payment"]["id"] for item in other_list.json()
    )

    cross = await auth_client.post(
        f"{PAYMENTS}/{data['payment']['id']}/confirm",
        headers=_auth(other_token),
    )
    assert cross.status_code == 404
