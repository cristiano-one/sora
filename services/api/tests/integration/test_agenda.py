"""Testes do motor de agenda: conflito, buffer, RBAC e disponibilidade."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.locks import acquire_lock, release_lock
from app.models import UserRole
from sqlalchemy import text

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = date(2027, 1, 10)
APPOINTMENTS = "/api/v1/appointments"
AVAILABILITY = "/api/v1/agenda/availability"
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
TENANTS = "/api/v1/tenants"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def _create_service(auth_client, token: str) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Serviço {uuid4().hex[:6]}",
            "duration_minutes": 60,
            "buffer_minutes": 10,
            "price": "100.00",
            "cost": "10.00",
            "requires_deposit": False,
            "show_average_price": True,
        },
    )
    assert response.status_code == 201
    return response.json()


async def _create_client(auth_client, token: str) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {suffix}",
            "phone": "(11) 91234-5678",
            "email": f"cliente-{suffix}@example.com",
        },
    )
    assert response.status_code == 201
    return response.json()


async def _create_appointment(
    auth_client,
    token: str,
    *,
    client_id: object,
    service_id: object,
    collaborator_id: object | None = None,
    starts_at: datetime | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "client_id": client_id,
        "service_id": service_id,
        "starts_at": (starts_at or _at(13)).isoformat(),
    }
    if collaborator_id is not None:
        payload["collaborator_id"] = collaborator_id

    response = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_owner_creates_appointment(auth_client, tenant_users) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)

    appointment = await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=str(collaborator.user_id),
        starts_at=_at(13),
    )

    starts = datetime.fromisoformat(str(appointment["starts_at"]))
    ends = datetime.fromisoformat(str(appointment["ends_at"]))

    assert ends - starts == timedelta(minutes=70)
    assert appointment["status"] == "SCHEDULED"
    assert appointment["client_name"] == client["full_name"]
    assert appointment["service_name"] == service["name"]


async def test_overlapping_appointment_is_rejected(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    collaborator_id = str(collaborator.user_id)

    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )

    response = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client["id"],
            "service_id": service["id"],
            "collaborator_id": collaborator_id,
            "starts_at": _at(13, 30).isoformat(),
        },
    )

    assert response.status_code == 409


async def test_adjacent_slot_is_allowed(auth_client, tenant_users) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    collaborator_id = str(collaborator.user_id)

    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )
    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(14, 10),
    )


async def test_collaborator_is_limited_to_own_agenda(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    owner_token = await _login(auth_client, owner)
    collab_token = await _login(auth_client, collaborator)
    service = await _create_service(auth_client, owner_token)
    client = await _create_client(auth_client, owner_token)

    await _create_appointment(
        auth_client,
        owner_token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=str(collaborator.user_id),
        starts_at=_at(13),
    )
    await _create_appointment(
        auth_client,
        owner_token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=str(owner.user_id),
        starts_at=_at(15),
    )

    forbidden = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(collab_token),
        json={
            "client_id": client["id"],
            "service_id": service["id"],
            "collaborator_id": str(owner.user_id),
            "starts_at": _at(16).isoformat(),
        },
    )
    assert forbidden.status_code == 403

    listing = await auth_client.get(
        APPOINTMENTS,
        headers=_auth(collab_token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )

    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 1
    assert data[0]["collaborator_id"] == str(collaborator.user_id)


async def test_cancel_frees_slot(auth_client, tenant_users) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    collaborator_id = str(collaborator.user_id)

    appointment = await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )

    cancelled = await auth_client.patch(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token),
        json={"status": "CANCELLED"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )


async def test_availability_excludes_occupied_slots(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    collaborator_id = str(collaborator.user_id)

    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )

    response = await auth_client.get(
        AVAILABILITY,
        headers=_auth(token),
        params={
            "service_id": service["id"],
            "date": DAY.isoformat(),
            "collaborator_id": collaborator_id,
        },
    )

    assert response.status_code == 200
    data = response.json()
    slots = data["available_slots"]
    assert data["duration_minutes"] == 60
    assert data["buffer_minutes"] == 10
    assert "13:00" not in slots
    assert "13:30" not in slots
    assert "14:00" not in slots
    assert "14:30" in slots


async def test_cross_tenant_appointment_returns_404(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    appointment = await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=str(collaborator.user_id),
        starts_at=_at(13),
    )

    suffix = uuid4().hex[:8]
    signup = await auth_client.post(
        TENANTS,
        json={
            "name": "Clínica B",
            "slug": f"clinica-b-{suffix}",
            "tax_regime": "COMPLETE",
            "owner_full_name": "Owner B",
            "owner_email": f"owner-b-{suffix}@example.com",
            "owner_password": "senha-forte-123",
        },
    )
    assert signup.status_code == 201

    login_b = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": f"clinica-b-{suffix}",
            "email": f"owner-b-{suffix}@example.com",
            "password": "senha-forte-123",
        },
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]

    get_response = await auth_client.get(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token_b),
    )
    patch_response = await auth_client.patch(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token_b),
        json={"status": "CANCELLED"},
    )

    assert get_response.status_code == 404
    assert patch_response.status_code == 404


async def test_reschedule_moves_appointment(auth_client, tenant_users) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    client = await _create_client(auth_client, token)
    collaborator_id = str(collaborator.user_id)

    appointment = await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )

    moved = await auth_client.patch(
        f"{APPOINTMENTS}/{appointment['id']}",
        headers=_auth(token),
        json={"starts_at": _at(16).isoformat()},
    )

    assert moved.status_code == 200
    starts = datetime.fromisoformat(str(moved.json()["starts_at"]))
    ends = datetime.fromisoformat(str(moved.json()["ends_at"]))
    assert ends - starts == timedelta(minutes=70)

    # O horário antigo ficou livre.
    await _create_appointment(
        auth_client,
        token,
        client_id=client["id"],
        service_id=service["id"],
        collaborator_id=collaborator_id,
        starts_at=_at(13),
    )

    # O horário novo está ocupado.
    conflict = await auth_client.post(
        APPOINTMENTS,
        headers=_auth(token),
        json={
            "client_id": client["id"],
            "service_id": service["id"],
            "collaborator_id": collaborator_id,
            "starts_at": _at(16).isoformat(),
        },
    )
    assert conflict.status_code == 409


async def test_redis_lock_prevents_concurrent_acquire(test_redis) -> None:
    key = "tenant:test:agenda:lock:collaborator"

    token = await acquire_lock(test_redis, key)
    assert token is not None
    assert await acquire_lock(test_redis, key) is None

    await release_lock(test_redis, key, "wrong-token")
    assert await acquire_lock(test_redis, key) is None

    await release_lock(test_redis, key, token)
    new_token = await acquire_lock(test_redis, key)
    assert new_token is not None


async def test_database_exclusion_constraint_exists(app_session) -> None:
    result = await app_session.execute(
        text(
            "SELECT conname, contype FROM pg_constraint "
            "WHERE conname = 'ex_appointments_no_overlap'"
        )
    )
    row = result.one()

    assert row.contype in (b"x", "x")
