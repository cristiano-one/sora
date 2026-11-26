"""Comanda digital: itens, crédito, fechamento e integração financeira."""

from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime.now(TZ).date()
APPT_DAY = TODAY + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"
SALES = "/api/v1/sales"
ACCOUNTS = "/api/v1/finance/accounts"
SETTINGS = "/api/v1/tenants/settings"
RUN_CREDITS = "/api/v1/ai/birthday-credits/run"
COMMISSIONS = "/api/v1/finance/commissions"
CASH_FLOW = "/api/v1/finance/cash-flow"
ENTRIES = "/api/v1/finance/entries"
INVENTORY = "/api/v1/inventory"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _at(hour: int = 10) -> datetime:
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


async def _appointment(
    auth_client,
    token: str,
    collaborator_id,
    *,
    price: str = "100.00",
    birth_date: str | None = None,
    hour: int = 10,
) -> tuple[dict, dict]:
    suffix = uuid4().hex[:6]
    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Serviço {suffix}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": price,
            "cost": "20.00",
        },
    )
    assert service.status_code == 201, service.text
    payload = {
        "full_name": f"Cliente Comanda {suffix}",
        "phone": f"119{uuid4().int % 10**8:08d}",
    }
    if birth_date:
        payload["birth_date"] = birth_date
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json=payload,
    )
    assert client.status_code == 201, client.text
    appointment = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client.json()["id"],
            "service_id": service.json()["id"],
            "collaborator_id": str(collaborator_id),
            "starts_at": _at(hour).isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text
    return client.json(), appointment.json()


async def _account(auth_client, token: str) -> dict:
    response = await auth_client.post(
        ACCOUNTS,
        headers=_auth(token),
        json={
            "name": f"Caixa Comanda {uuid4().hex[:5]}",
            "type": "CASH",
            "initial_balance": "0.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_sale_flow_with_items_credit_close_and_commission(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    account = await _account(auth_client, token)
    birth = (TODAY + timedelta(days=2)).replace(year=1994)
    client, appointment = await _appointment(
        auth_client,
        token,
        collaborator.user_id,
        birth_date=birth.isoformat(),
    )
    await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={"birthday_credit_amount": "30.00"},
    )
    await auth_client.post(RUN_CREDITS, headers=_auth(token))
    credits = await auth_client.get(
        f"{CLIENTS}/{client['id']}/credits",
        headers=_auth(token),
    )
    credit = next(
        item for item in credits.json() if item["reason"] == "BIRTHDAY"
    )

    sale = await auth_client.post(
        f"{SALES}/from-appointment/{appointment['id']}",
        headers=_auth(token),
    )
    assert sale.status_code == 200, sale.text
    body = sale.json()
    assert body["status"] == "OPEN"
    assert body["subtotal"] == "100.00"
    assert body["total"] == "100.00"
    assert body["items"][0]["description"].startswith("Serviço")

    again = await auth_client.post(
        f"{SALES}/from-appointment/{appointment['id']}",
        headers=_auth(token),
    )
    assert again.json()["id"] == body["id"]

    item = await auth_client.post(
        f"{SALES}/{body['id']}/items",
        headers=_auth(token),
        json={
            "category": "PRODUCT",
            "description": "Produto teste",
            "quantity": 2,
            "unit_price": "25.00",
            "cost": "5.00",
        },
    )
    assert item.status_code == 201, item.text
    assert item.json()["subtotal"] == "150.00"

    discounted = await auth_client.patch(
        f"{SALES}/{body['id']}",
        headers=_auth(token),
        json={"discount": "10.00"},
    )
    assert discounted.status_code == 200
    assert discounted.json()["total"] == "140.00"

    with_credit = await auth_client.post(
        f"{SALES}/{body['id']}/credits",
        headers=_auth(token),
        json={"credit_id": credit["id"], "amount": "30.00"},
    )
    assert with_credit.status_code == 200, with_credit.text
    assert with_credit.json()["credit_amount"] == "30.00"
    assert with_credit.json()["total"] == "110.00"

    closed = await auth_client.post(
        f"{SALES}/{body['id']}/close",
        headers=_auth(token),
        json={
            "payment_method": "PIX",
            "account_id": account["id"],
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "PAID"
    assert closed.json()["financial_entry_id"] is not None

    entries = await auth_client.get(
        ENTRIES,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    sale_entry = next(
        item for item in entries.json() if item["amount"] == "110.00"
    )
    assert sale_entry["category"] == "SERVICE"
    assert sale_entry["status"] == "PAID"

    cash = await auth_client.get(
        CASH_FLOW,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert cash.json()["inflows"] == "110.00"

    commissions = await auth_client.get(
        COMMISSIONS,
        headers=_auth(token),
        params={
            "from_date": APPT_DAY.isoformat(),
            "to_date": APPT_DAY.isoformat(),
        },
    )
    assert commissions.status_code == 200
    assert commissions.json()["total"] == "45.00"

    appointment_after = await auth_client.get(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token),
    )
    assert appointment_after.json()["status"] == "COMPLETED"

    cancel_paid = await auth_client.post(
        f"{SALES}/{body['id']}/cancel",
        headers=_auth(token),
    )
    assert cancel_paid.status_code == 422


async def test_sale_stock_cancel_rbac_and_cross_tenant(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    account = await _account(auth_client, token)
    _, appointment = await _appointment(auth_client, token, collaborator.user_id)

    inventory = await auth_client.post(
        INVENTORY,
        headers=_auth(token),
        json={
            "name": f"Produto {uuid4().hex[:5]}",
            "unit": "un",
            "quantity": "5",
            "min_quantity": "1",
            "unit_cost": "10.00",
        },
    )
    assert inventory.status_code == 201

    sale = await auth_client.post(
        f"{SALES}/from-appointment/{appointment['id']}",
        headers=_auth(token),
    )
    item = await auth_client.post(
        f"{SALES}/{sale.json()['id']}/items",
        headers=_auth(token),
        json={
            "category": "PRODUCT",
            "inventory_item_id": inventory.json()["id"],
            "description": "Produto estoque",
            "quantity": 2,
            "unit_price": "30.00",
        },
    )
    assert item.status_code == 201, item.text
    closed = await auth_client.post(
        f"{SALES}/{sale.json()['id']}/close",
        headers=_auth(token),
        json={
            "payment_method": "CASH",
            "account_id": account["id"],
        },
    )
    assert closed.status_code == 200, closed.text

    inventory_after = await auth_client.get(
        f"{INVENTORY}/{inventory.json()['id']}/movements",
        headers=_auth(token),
    )
    assert inventory_after.status_code == 200
    assert inventory_after.json()[0]["kind"] == "OUT"
    assert inventory_after.json()[0]["quantity"] == "2.000"

    _, appointment_two = await _appointment(
        auth_client,
        token,
        collaborator.user_id,
        hour=11,
    )
    sale_two = await auth_client.post(
        f"{SALES}/from-appointment/{appointment_two['id']}",
        headers=_auth(token),
    )
    cancelled = await auth_client.post(
        f"{SALES}/{sale_two.json()['id']}/cancel",
        headers=_auth(token),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    collaborator_token = await _login(auth_client, collaborator)
    forbidden = await auth_client.get(
        SALES,
        headers=_auth(collaborator_token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert forbidden.status_code == 403

    other_token = await _login(auth_client, auth_user)
    cross = await auth_client.get(
        f"{SALES}/{sale.json()['id']}",
        headers=_auth(other_token),
    )
    assert cross.status_code == 404
