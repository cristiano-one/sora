"""Consumo de cotas de assinatura no agendamento interno e público."""

from datetime import UTC, date, datetime, time, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import settings
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime.now(TZ).date()
DAY = TODAY + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
PLANS = "/api/v1/subscription-plans"
SUBSCRIPTIONS = "/api/v1/subscriptions"
APPOINTMENTS = "/api/v1/appointments"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _internal() -> dict[str, str]:
    return {"X-Internal-Token": settings.internal_api_token}


def _phone() -> str:
    return f"119{uuid4().int % 10**8:08d}"


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=TZ).astimezone(UTC)


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


async def _create_service(
    auth_client,
    token: str,
    *,
    requires_deposit: bool = True,
) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Serviço {uuid4().hex[:6]}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "120.00",
            "cost": "20.00",
            "requires_deposit": requires_deposit,
            "deposit_amount": "30.00" if requires_deposit else None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_client(
    auth_client,
    token: str,
    *,
    phone: str | None = None,
) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {suffix}",
            "phone": phone or _phone(),
            "email": f"cliente-{suffix}@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_plan(
    auth_client,
    token: str,
    service_id: object,
    *,
    uses_per_cycle: int = 4,
    min_interval_days: int | None = None,
    allowed_weekdays: list[int] | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "service_id": service_id,
        "uses_per_cycle": uses_per_cycle,
    }
    if min_interval_days is not None:
        item["min_interval_days"] = min_interval_days
    if allowed_weekdays is not None:
        item["allowed_weekdays"] = allowed_weekdays
    response = await auth_client.post(
        PLANS,
        headers=_auth(token),
        json={
            "name": f"Clube {uuid4().hex[:6]}",
            "price": "199.90",
            "billing_cycle": "MONTHLY",
            "items": [item],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _contract(
    auth_client,
    token: str,
    *,
    client_id: object,
    plan_id: object,
) -> dict[str, object]:
    response = await auth_client.post(
        f"{CLIENTS}/{client_id}/subscriptions",
        headers=_auth(token),
        json={"plan_id": plan_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _book(
    auth_client,
    token: str,
    *,
    client_id: object,
    service_id: object,
    collaborator_id: object,
    starts_at: datetime,
) -> dict[str, object]:
    response = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client_id,
            "service_id": service_id,
            "collaborator_id": str(collaborator_id),
            "starts_at": starts_at.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _magic_link(auth_client, slug: str, phone: str) -> str:
    response = await auth_client.post(
        f"/api/v1/public/{slug}/magic-link",
        headers=_internal(),
        json={"phone": phone},
    )
    assert response.status_code == 200, response.text
    return parse_qs(urlparse(response.json()["url"]).query)["t"][0]


async def _quota_used(auth_client, token: str, subscription_id: str) -> int:
    response = await auth_client.get(SUBSCRIPTIONS, headers=_auth(token))
    assert response.status_code == 200
    item = next(
        value for value in response.json() if value["id"] == subscription_id
    )
    return int(item["quotas"][0]["used"])


async def test_internal_booking_consumes_quota_and_waives_deposit(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(
        auth_client,
        token,
        service["id"],
        uses_per_cycle=1,
    )
    client = await _create_client(auth_client, token)
    subscription = await _contract(
        auth_client,
        token,
        client_id=client["id"],
        plan_id=plan["id"],
    )

    appointment = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY, 10),
    )

    assert appointment["status"] == "SCHEDULED"
    assert appointment["deposit_amount"] is None
    assert appointment["subscription_id"] == subscription["id"]
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 1

    second = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY, 11),
    )
    assert second["status"] == "PENDING_DEPOSIT"
    assert second["deposit_amount"] == "30.00"
    assert second["subscription_id"] is None


async def test_public_booking_consumes_quota(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(
        auth_client,
        token,
        service["id"],
        uses_per_cycle=2,
    )
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    subscription = await _contract(
        auth_client,
        token,
        client_id=client["id"],
        plan_id=plan["id"],
    )
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)

    response = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/appointments",
        params={"t": magic},
        json={
            "service_id": service["id"],
            "collaborator_id": str(collaborator.user_id),
            "starts_at": _at(DAY, 13).isoformat(),
            "full_name": client["full_name"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["deposit_amount"] is None
    assert body["used_subscription"] is True
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 1


async def test_cancel_releases_quota_for_new_booking(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token, requires_deposit=False)
    plan = await _create_plan(
        auth_client,
        token,
        service["id"],
        uses_per_cycle=1,
    )
    client = await _create_client(auth_client, token)
    subscription = await _contract(
        auth_client,
        token,
        client_id=client["id"],
        plan_id=plan["id"],
    )
    appointment = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY, 14),
    )
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 1

    cancelled = await auth_client.patch(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token),
        json={"status": "CANCELLED"},
    )
    assert cancelled.status_code == 200
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 0

    rebooked = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY, 14),
    )
    assert rebooked["subscription_id"] == subscription["id"]
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 1


async def test_min_interval_falls_back_to_paid_booking(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(
        auth_client,
        token,
        service["id"],
        uses_per_cycle=4,
        min_interval_days=7,
    )
    client = await _create_client(auth_client, token)
    subscription = await _contract(
        auth_client,
        token,
        client_id=client["id"],
        plan_id=plan["id"],
    )

    first = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY, 15),
    )
    assert first["subscription_id"] == subscription["id"]

    second = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(DAY + timedelta(days=1), 15),
    )
    assert second["subscription_id"] is None
    assert second["status"] == "PENDING_DEPOSIT"
    assert await _quota_used(auth_client, token, str(subscription["id"])) == 1


async def test_allowed_weekdays_restrict_quota(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    plan = await _create_plan(
        auth_client,
        token,
        service["id"],
        uses_per_cycle=4,
        allowed_weekdays=[3],  # quinta-feira
    )
    client = await _create_client(auth_client, token)
    subscription = await _contract(
        auth_client,
        token,
        client_id=client["id"],
        plan_id=plan["id"],
    )
    days_ahead = (3 - TODAY.weekday()) % 7
    thursday_day = TODAY + timedelta(days=days_ahead + 7)
    monday_day = thursday_day - timedelta(days=3)

    monday = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(monday_day, 16),
    )
    assert monday["subscription_id"] is None
    assert monday["status"] == "PENDING_DEPOSIT"

    thursday = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(thursday_day, 16),
    )
    assert thursday["subscription_id"] == subscription["id"]
    assert thursday["status"] == "SCHEDULED"
