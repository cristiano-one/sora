"""Folha de pagamento: verbas, integração financeira e isolamento."""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime.now(TZ).date()
LOGIN = "/api/v1/auth/login"
PAYROLL = "/api/v1/payroll"
ACCOUNTS = "/api/v1/finance/accounts"
ENTRIES = "/api/v1/finance/entries"
CASH_FLOW = "/api/v1/finance/cash-flow"


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


async def _account(auth_client, token: str) -> dict:
    response = await auth_client.post(
        ACCOUNTS,
        headers=_auth(token),
        json={
            "name": f"Caixa Folha {uuid4().hex[:5]}",
            "type": "CASH",
            "initial_balance": "5000.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_payroll_paid_creates_and_syncs_financial_entry(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    account = await _account(auth_client, token)

    advance = await auth_client.post(
        PAYROLL,
        headers=_auth(token),
        json={
            "user_id": str(collaborator.user_id),
            "kind": "ADVANCE",
            "description": "Adiantamento quinzenal",
            "amount": "500.00",
            "competence_date": TODAY.isoformat(),
        },
    )
    assert advance.status_code == 201, advance.text
    assert advance.json()["status"] == "PENDING"
    assert advance.json()["financial_entry_id"] is None

    salary = await auth_client.post(
        PAYROLL,
        headers=_auth(token),
        json={
            "user_id": str(collaborator.user_id),
            "kind": "SALARY",
            "description": "Salário do mês",
            "amount": "1000.00",
            "competence_date": TODAY.isoformat(),
            "status": "PAID",
            "cash_date": TODAY.isoformat(),
            "account_id": account["id"],
        },
    )
    assert salary.status_code == 201, salary.text
    salary_data = salary.json()
    assert salary_data["financial_entry_id"] is not None

    entries = await auth_client.get(
        ENTRIES,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert entries.status_code == 200
    payroll_entries = [
        item for item in entries.json() if item["category"] == "PAYROLL"
    ]
    assert len(payroll_entries) == 1
    assert payroll_entries[0]["amount"] == "1000.00"
    assert payroll_entries[0]["status"] == "PAID"

    cash = await auth_client.get(
        CASH_FLOW,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert cash.status_code == 200
    assert cash.json()["outflows"] == "1000.00"

    updated = await auth_client.patch(
        f"{PAYROLL}/{salary_data['id']}",
        headers=_auth(token),
        json={"amount": "1200.00"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == "1200.00"

    reverted = await auth_client.patch(
        f"{PAYROLL}/{salary_data['id']}",
        headers=_auth(token),
        json={"status": "PENDING"},
    )
    assert reverted.status_code == 200, reverted.text
    assert reverted.json()["financial_entry_id"] is None

    entries_after = await auth_client.get(
        ENTRIES,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert all(
        item["category"] != "PAYROLL" for item in entries_after.json()
    )

    listing = await auth_client.get(
        PAYROLL,
        headers=_auth(token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    deleted = await auth_client.delete(
        f"{PAYROLL}/{advance.json()['id']}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204


async def test_payroll_is_owner_only_and_cross_tenant_hidden(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    entry = await auth_client.post(
        PAYROLL,
        headers=_auth(token),
        json={
            "user_id": str(collaborator.user_id),
            "kind": "PRO_LABORE",
            "description": "Pró-labore",
            "amount": "2000.00",
            "competence_date": TODAY.isoformat(),
        },
    )
    assert entry.status_code == 201

    for role in (UserRole.ADMIN, UserRole.COLLABORATOR):
        other_token = await _login(auth_client, tenant_users.users[role])
        forbidden = await auth_client.get(
            PAYROLL,
            headers=_auth(other_token),
            params={
                "from_date": TODAY.isoformat(),
                "to_date": TODAY.isoformat(),
            },
        )
        assert forbidden.status_code == 403

    other_token = await _login(auth_client, auth_user)
    other_list = await auth_client.get(
        PAYROLL,
        headers=_auth(other_token),
        params={
            "from_date": TODAY.isoformat(),
            "to_date": TODAY.isoformat(),
        },
    )
    assert other_list.status_code == 200
    assert other_list.json() == []

    cross = await auth_client.delete(
        f"{PAYROLL}/{entry.json()['id']}",
        headers=_auth(other_token),
    )
    assert cross.status_code == 404
