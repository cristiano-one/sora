"""Automações: regras padrão, agendamento, execução e RBAC."""

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
RULES = "/api/v1/automations/rules"
RUNS = "/api/v1/automations/runs"
RUN = "/api/v1/automations/run"


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


async def _appointment(auth_client, token: str, collaborator_id, hour: int) -> dict:
    suffix = uuid4().hex[:6]
    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Automação {suffix}",
            "duration_minutes": 30,
            "buffer_minutes": 0,
            "price": "80.00",
            "cost": "10.00",
        },
    )
    assert service.status_code == 201, service.text
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": "Cliente Automação",
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
            "starts_at": datetime.combine(DAY, time(hour), tzinfo=TZ).isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text
    return appointment.json()


async def test_default_rules_schedule_and_run(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    appointment = await _appointment(
        auth_client,
        token,
        collaborator.user_id,
        hour=10,
    )

    rules = await auth_client.get(RULES, headers=_auth(token))
    assert rules.status_code == 200, rules.text
    triggers = {item["trigger"] for item in rules.json()}
    assert {
        "BOOKING_CONFIRMATION",
        "REMINDER_24H",
        "REMINDER_2H",
        "POST_SERVICE",
        "WINBACK_60D",
        "BIRTHDAY",
    } <= triggers
    reminder = next(
        item for item in rules.json() if item["trigger"] == "REMINDER_2H"
    )
    assert reminder["is_active"] is True

    runs = await auth_client.get(RUNS, headers=_auth(token))
    assert runs.status_code == 200
    assert any(
        run["appointment_id"] == appointment["id"] for run in runs.json()
    )

    executed = await auth_client.post(RUN, headers=_auth(token))
    assert executed.status_code == 200, executed.text
    assert executed.json()["processed"] >= 1
    assert executed.json()["sent"] >= 1

    after = await auth_client.get(RUNS, headers=_auth(token))
    sent = [
        item
        for item in after.json()
        if item["appointment_id"] == appointment["id"]
        and item["status"] == "SENT"
    ]
    assert sent

    disabled = await auth_client.patch(
        f"{RULES}/{reminder['id']}",
        headers=_auth(token),
        json={"is_active": False, "template": "Lembrete desativado"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert disabled.json()["template"] == "Lembrete desativado"

    second = await _appointment(
        auth_client,
        token,
        collaborator.user_id,
        hour=11,
    )
    runs_second = await auth_client.get(RUNS, headers=_auth(token))
    reminder_runs = [
        item
        for item in runs_second.json()
        if item["appointment_id"] == second["id"]
        and item["rule_id"] == reminder["id"]
    ]
    assert reminder_runs == []


async def test_automations_are_manager_only(
    auth_client,
    tenant_users,
) -> None:
    collaborator_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    for endpoint in (RULES, RUNS):
        response = await auth_client.get(
            endpoint,
            headers=_auth(collaborator_token),
        )
        assert response.status_code == 403

    admin_token = await _login(
        auth_client,
        tenant_users.users[UserRole.ADMIN],
    )
    allowed = await auth_client.get(RULES, headers=_auth(admin_token))
    assert allowed.status_code == 200
