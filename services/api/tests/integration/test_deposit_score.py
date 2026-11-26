"""Score mínimo, sinal configurável e expiração de reserva."""

from datetime import UTC, datetime, time, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import settings
from app.db.rls import set_tenant_context
from app.models import Appointment, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"
SETTINGS = "/api/v1/tenants/settings"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _internal() -> dict[str, str]:
    return {"X-Internal-Token": settings.internal_api_token}


def _phone() -> str:
    return f"119{uuid4().int % 10**8:08d}"


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(DAY, time(hour, minute), tzinfo=TZ).astimezone(UTC)


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
    requires_deposit: bool = False,
    deposit_amount: str | None = None,
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
            "deposit_amount": deposit_amount,
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


async def _set_score(auth_client, token: str, client_id: object, score: int) -> None:
    response = await auth_client.patch(
        f"{CLIENTS}/{client_id}",
        headers=_auth(token),
        json={"score": score},
    )
    assert response.status_code == 200, response.text


async def _patch_settings(auth_client, token: str, body: dict[str, object]):
    return await auth_client.patch(SETTINGS, headers=_auth(token), json=body)


async def _book(
    auth_client,
    token: str,
    *,
    client_id: object,
    service_id: object,
    collaborator_id: object,
    starts_at: datetime,
):
    return await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client_id,
            "service_id": service_id,
            "collaborator_id": str(collaborator_id),
            "starts_at": starts_at.isoformat(),
        },
    )


async def _magic_link(auth_client, slug: str, phone: str) -> str:
    response = await auth_client.post(
        f"/api/v1/public/{slug}/magic-link",
        headers=_internal(),
        json={"phone": phone},
    )
    assert response.status_code == 200, response.text
    return parse_qs(urlparse(response.json()["url"]).query)["t"][0]


async def test_owner_reads_and_updates_settings(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)

    defaults = await auth_client.get(SETTINGS, headers=_auth(token))
    assert defaults.status_code == 200
    assert defaults.json() == {
        "deposit_score_threshold": None,
        "deposit_amount_low_score": None,
        "theme_primary_color": "#4f46e5",
        "agent_name": "Sora",
        "enable_tithe_and_offering": False,
        "tithe_percentage": "10.00",
        "offering_amount": "0.00",
    }

    updated = await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
            "theme_primary_color": "#0ea5e9",
            "agent_name": "Bia",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["deposit_score_threshold"] == 70
    assert updated.json()["deposit_amount_low_score"] == "50.00"
    assert updated.json()["theme_primary_color"] == "#0ea5e9"

    persisted = await auth_client.get(SETTINGS, headers=_auth(token))
    assert persisted.json()["agent_name"] == "Bia"

    magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )
    context = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/context",
        params={"t": magic},
    )
    assert context.status_code == 200
    assert context.json()["theme_primary_color"] == "#0ea5e9"


async def test_threshold_requires_positive_amount(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)

    invalid = await _patch_settings(
        auth_client,
        token,
        {"deposit_score_threshold": 70},
    )
    assert invalid.status_code == 422

    amount_only = await _patch_settings(
        auth_client,
        token,
        {"deposit_amount_low_score": "50.00"},
    )
    assert amount_only.status_code == 200
    assert amount_only.json()["deposit_score_threshold"] is None

    valid = await _patch_settings(
        auth_client,
        token,
        {"deposit_score_threshold": 70},
    )
    assert valid.status_code == 200
    assert valid.json()["deposit_amount_low_score"] == "50.00"


async def test_low_score_requires_deposit_internal(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    await _set_score(auth_client, token, client["id"], 40)
    await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
        },
    )

    response = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(10),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING_DEPOSIT"
    assert body["deposit_amount"] == "50.00"
    assert body["subscription_id"] is None


async def test_high_score_skips_low_score_deposit(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    await _set_score(auth_client, token, client["id"], 90)
    await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
        },
    )

    response = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(11),
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "SCHEDULED"
    assert response.json()["deposit_amount"] is None


async def test_service_deposit_still_applies_for_high_score(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(
        auth_client,
        token,
        requires_deposit=True,
        deposit_amount="30.00",
    )
    client = await _create_client(auth_client, token)
    await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
        },
    )

    response = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(12),
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "PENDING_DEPOSIT"
    assert response.json()["deposit_amount"] == "30.00"


async def test_public_low_score_requires_deposit_without_leak(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    await _set_score(auth_client, token, client["id"], 25)
    await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
        },
    )
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)

    response = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/appointments",
        params={"t": magic},
        json={
            "service_id": service["id"],
            "collaborator_id": str(collaborator.user_id),
            "starts_at": _at(13).isoformat(),
            "full_name": client["full_name"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING_DEPOSIT"
    assert body["deposit_amount"] == "50.00"
    assert body["used_subscription"] is False
    for forbidden in ("score", "is_blocked", "low_score"):
        assert forbidden not in response.text


async def test_expired_pending_deposit_frees_slot(
    auth_client,
    app_session: AsyncSession,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    await _set_score(auth_client, token, client["id"], 40)
    await _patch_settings(
        auth_client,
        token,
        {
            "deposit_score_threshold": 70,
            "deposit_amount_low_score": "50.00",
        },
    )
    created = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(14),
    )
    assert created.status_code == 201, created.text
    appointment_id = UUID(created.json()["id"])

    await set_tenant_context(app_session, tenant_users.tenant_id)
    appointment = await app_session.get(Appointment, appointment_id)
    assert appointment is not None
    appointment.deposit_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await app_session.commit()

    availability = await auth_client.get(
        "/api/v1/agenda/availability",
        headers=_auth(token),
        params={
            "service_id": service["id"],
            "date": DAY.isoformat(),
            "collaborator_id": str(collaborator.user_id),
        },
    )
    assert availability.status_code == 200
    assert "14:00" in availability.json()["available_slots"]

    listed = await auth_client.get(
        APPOINTMENTS,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert listed.status_code == 200
    expired = next(
        item for item in listed.json() if item["id"] == str(appointment_id)
    )
    assert expired["status"] == "EXPIRED"

    rebooked = await _book(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(14),
    )
    assert rebooked.status_code == 201, rebooked.text


async def test_collaborator_cannot_access_settings(
    auth_client,
    tenant_users,
) -> None:
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, collaborator)

    read = await auth_client.get(SETTINGS, headers=_auth(token))
    assert read.status_code == 403

    update = await _patch_settings(
        auth_client,
        token,
        {"theme_primary_color": "#000000"},
    )
    assert update.status_code == 403


async def test_settings_are_isolated_between_tenants(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    token = await _login(auth_client, owner)
    updated = await _patch_settings(
        auth_client,
        token,
        {"theme_primary_color": "#123456"},
    )
    assert updated.status_code == 200

    other_token = await _login(auth_client, auth_user)
    other = await auth_client.get(SETTINGS, headers=_auth(other_token))
    assert other.status_code == 200
    assert other.json()["theme_primary_color"] == "#4f46e5"
