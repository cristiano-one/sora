"""Testes do módulo financeiro: caixa, DRE, comissões e RBAC."""

from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = date(2027, 2, 1)
APPT_DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
ACCOUNTS = "/api/v1/finance/accounts"
ENTRIES = "/api/v1/finance/entries"
CASH_FLOW = "/api/v1/finance/cash-flow"
DRE = "/api/v1/finance/dre"
COMMISSIONS = "/api/v1/finance/commissions"
MY_COMMISSION = "/api/v1/finance/my-commission"
SALES = "/api/v1/finance/sales"
EXPORT = "/api/v1/finance/export"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"
SETTINGS = "/api/v1/tenants/settings"


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


async def _create_account(
    auth_client,
    token: str,
    *,
    name: str = "Caixa",
    initial_balance: str = "100.00",
) -> dict[str, object]:
    response = await auth_client.post(
        ACCOUNTS,
        headers=_auth(token),
        json={
            "name": f"{name} {uuid4().hex[:4]}",
            "type": "CASH",
            "initial_balance": initial_balance,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_entry(
    auth_client,
    token: str,
    *,
    account_id: object,
    entry_type: str,
    category: str,
    amount: str,
    status: str = "PAID",
    cash_date: str | None = DAY.isoformat(),
    description: str = "Lançamento",
):
    return await auth_client.post(
        ENTRIES,
        headers=_auth(token),
        json={
            "account_id": account_id,
            "type": entry_type,
            "category": category,
            "description": description,
            "amount": amount,
            "competence_date": DAY.isoformat(),
            "cash_date": cash_date,
            "status": status,
        },
    )


async def test_owner_manages_accounts_entries_and_reports(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    account = await _create_account(auth_client, token)

    income = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="INCOME",
        category="SERVICE",
        amount="1000.00",
    )
    assert income.status_code == 201, income.text

    expense = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="EXPENSE",
        category="RENT",
        amount="200.00",
    )
    assert expense.status_code == 201, expense.text

    pending = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="INCOME",
        category="PRODUCT",
        amount="300.00",
        status="PENDING",
        cash_date=None,
    )
    assert pending.status_code == 201, pending.text

    listed = await auth_client.get(ENTRIES, headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    cash = await auth_client.get(
        CASH_FLOW,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert cash.status_code == 200, cash.text
    body = cash.json()
    assert body["opening_balance"] == "100.00"
    assert body["inflows"] == "1000.00"
    assert body["outflows"] == "200.00"
    assert body["closing_balance"] == "900.00"

    balances = await auth_client.get(
        f"{ACCOUNTS}/balances",
        headers=_auth(token),
    )
    assert balances.status_code == 200
    assert balances.json()[0]["balance"] == "900.00"

    dre = await auth_client.get(
        DRE,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert dre.status_code == 200, dre.text
    data = dre.json()
    assert data["gross_revenue"] == "1000.00"
    assert data["operating_expenses"] == "200.00"
    assert data["net_profit"] == "800.00"
    assert data["tithe_enabled"] is False
    assert data["after_tithe_and_offering"] == "800.00"

    exported = await auth_client.get(
        EXPORT,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "1000.00" in exported.text
    assert "attachment" in exported.headers["content-disposition"]


async def test_paid_entry_requires_cash_date(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    account = await _create_account(auth_client, token)

    response = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="INCOME",
        category="SERVICE",
        amount="100.00",
        cash_date=None,
    )

    assert response.status_code == 422


async def test_commissions_and_net_sales_from_completed_appointments(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)

    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Corte {uuid4().hex[:5]}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "100.00",
            "cost": "20.00",
        },
    )
    assert service.status_code == 201, service.text

    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {uuid4().hex[:6]}",
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
            "collaborator_id": str(collaborator.user_id),
            "starts_at": _at().isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text

    completed = await auth_client.patch(
        f"{APPOINTMENTS}/{appointment.json()['id']}",
        headers=_auth(token),
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text

    commissions = await auth_client.get(
        COMMISSIONS,
        headers=_auth(token),
        params={
            "from_date": APPT_DAY.isoformat(),
            "to_date": APPT_DAY.isoformat(),
        },
    )
    assert commissions.status_code == 200, commissions.text
    item = commissions.json()["items"][0]
    assert item["collaborator_id"] == str(collaborator.user_id)
    assert item["completed_appointments"] == 1
    assert item["gross_revenue"] == "100.00"
    assert item["commission_amount"] == "45.00"
    assert commissions.json()["total"] == "45.00"

    collaborator_token = await _login(auth_client, collaborator)
    mine = await auth_client.get(
        MY_COMMISSION,
        headers=_auth(collaborator_token),
        params={
            "from_date": APPT_DAY.isoformat(),
            "to_date": APPT_DAY.isoformat(),
        },
    )
    assert mine.status_code == 200, mine.text
    assert len(mine.json()["items"]) == 1
    assert mine.json()["items"][0]["collaborator_id"] == str(
        collaborator.user_id
    )
    assert mine.json()["total"] == "45.00"

    owner_mine = await auth_client.get(
        MY_COMMISSION,
        headers=_auth(token),
        params={
            "from_date": APPT_DAY.isoformat(),
            "to_date": APPT_DAY.isoformat(),
        },
    )
    assert owner_mine.status_code == 200
    assert owner_mine.json()["items"] == []

    sales = await auth_client.get(
        SALES,
        headers=_auth(token),
        params={
            "from_date": APPT_DAY.isoformat(),
            "to_date": APPT_DAY.isoformat(),
        },
    )
    assert sales.status_code == 200, sales.text
    sale = sales.json()["items"][0]
    assert sale["gross_amount"] == "100.00"
    assert sale["cost_amount"] == "20.00"
    assert sale["commission_amount"] == "45.00"
    assert sale["net_amount"] == "35.00"


async def test_finance_is_owner_only(
    auth_client,
    tenant_users,
) -> None:
    admin = tenant_users.users[UserRole.ADMIN]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    for user in (admin, collaborator):
        token = await _login(auth_client, user)
        for endpoint in (
            ACCOUNTS,
            CASH_FLOW,
            DRE,
            COMMISSIONS,
            SALES,
            EXPORT,
        ):
            params = (
                {"from_date": DAY.isoformat(), "to_date": DAY.isoformat()}
                if endpoint not in (ACCOUNTS,)
                else None
            )
            response = await auth_client.get(
                endpoint,
                headers=_auth(token),
                params=params,
            )
            assert response.status_code == 403, (
                user.role,
                endpoint,
                response.status_code,
            )


async def test_finance_is_isolated_between_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    account = await _create_account(auth_client, token)
    entry = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="INCOME",
        category="SERVICE",
        amount="500.00",
    )
    assert entry.status_code == 201

    other_token = await _login(auth_client, auth_user)
    accounts = await auth_client.get(ACCOUNTS, headers=_auth(other_token))
    assert accounts.status_code == 200
    assert accounts.json() == []

    entries = await auth_client.get(ENTRIES, headers=_auth(other_token))
    assert entries.status_code == 200
    assert entries.json() == []

    cross = await auth_client.patch(
        f"{ACCOUNTS}/{account['id']}",
        headers=_auth(other_token),
        json={"name": "Invadida"},
    )
    assert cross.status_code == 404


async def test_tithe_and_offering_in_dre(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    settings = await auth_client.patch(
        SETTINGS,
        headers=_auth(token),
        json={
            "enable_tithe_and_offering": True,
            "tithe_percentage": "10.00",
            "offering_amount": "50.00",
        },
    )
    assert settings.status_code == 200, settings.text

    account = await _create_account(auth_client, token)
    await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="INCOME",
        category="SERVICE",
        amount="1000.00",
    )
    await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="EXPENSE",
        category="RENT",
        amount="100.00",
    )

    dre = await auth_client.get(
        DRE,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert dre.status_code == 200, dre.text
    data = dre.json()
    assert data["net_profit"] == "900.00"
    assert data["tithe_enabled"] is True
    assert data["tithe_amount"] == "90.00"
    assert data["offering_amount"] == "50.00"
    assert data["after_tithe_and_offering"] == "760.00"


async def test_export_sanitizes_formula_injection(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    account = await _create_account(auth_client, token)
    response = await _create_entry(
        auth_client,
        token,
        account_id=account["id"],
        entry_type="EXPENSE",
        category="OTHER_EXPENSE",
        amount="10.00",
        description="=SUM(A1:A9)",
    )
    assert response.status_code == 201

    exported = await auth_client.get(
        EXPORT,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert exported.status_code == 200
    assert "'=SUM(A1:A9)" in exported.text
