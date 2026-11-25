"""Testes do link mágico e agendamento público (Zero-Leak)."""

from datetime import UTC, date, datetime, time
from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import settings
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = date(2027, 1, 20)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _internal() -> dict[str, str]:
    return {"X-Internal-Token": settings.internal_api_token}


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(DAY, time(hour, minute), tzinfo=TZ).astimezone(UTC)


def _phone() -> str:
    return f"119{uuid4().int % 10**8:08d}"


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
    show_average_price: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": f"Serviço {uuid4().hex[:6]}",
        "duration_minutes": 60,
        "buffer_minutes": 10,
        "price": "120.00",
        "cost": "20.00",
        "requires_deposit": requires_deposit,
        "show_average_price": show_average_price,
    }
    if deposit_amount is not None:
        payload["deposit_amount"] = deposit_amount
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json=payload,
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


async def _magic_link(
    auth_client,
    slug: str,
    phone: str,
) -> tuple[str, str]:
    response = await auth_client.post(
        f"/api/v1/public/{slug}/magic-link",
        headers=_internal(),
        json={"phone": phone},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    token = parse_qs(urlparse(body["url"]).query)["t"][0]
    return body["url"], token


async def _public_booking(
    auth_client,
    *,
    slug: str,
    token: str,
    service_id: object,
    collaborator_id: object,
    starts_at: datetime,
    full_name: str = "Cliente Público",
):
    return await auth_client.post(
        f"/api/v1/public/{slug}/appointments",
        params={"t": token},
        json={
            "service_id": str(service_id),
            "collaborator_id": str(collaborator_id),
            "starts_at": starts_at.isoformat(),
            "full_name": full_name,
        },
    )


async def test_magic_link_requires_internal_token(
    auth_client,
    tenant_users,
) -> None:
    phone = _phone()

    missing = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/magic-link",
        json={"phone": phone},
    )
    assert missing.status_code == 401

    wrong = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/magic-link",
        headers={"X-Internal-Token": "token-errado"},
        json={"phone": phone},
    )
    assert wrong.status_code == 401

    ok = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/magic-link",
        headers=_internal(),
        json={"phone": phone},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["url"].startswith(settings.public_booking_base_url)
    assert f"/public/{tenant_users.tenant_slug}?t=" in body["url"]
    assert body["expires_in"] == 20 * 60


async def test_magic_link_uses_tenant_scoped_key_with_ttl(
    auth_client,
    tenant_users,
    test_redis,
) -> None:
    phone = _phone()
    _, token = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        phone,
    )

    key = f"tenant:{tenant_users.tenant_id}:public:magic:{token}"
    assert await test_redis.get(key) == phone
    ttl = await test_redis.ttl(key)
    assert 0 < ttl <= 20 * 60
    assert await test_redis.exists(f"public:magic:{token}") == 0


async def test_context_exposes_only_public_data(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    visible = await _create_service(auth_client, token)
    hidden = await _create_service(
        auth_client,
        token,
        show_average_price=False,
    )
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        phone,
    )

    response = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/context",
        params={"t": magic},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "tenant_name",
        "tenant_slug",
        "client_name",
        "services",
        "professionals",
        "plans",
        "subscription",
    }
    assert body["tenant_slug"] == tenant_users.tenant_slug
    assert body["client_name"] == client["full_name"]

    services = {item["id"]: item for item in body["services"]}
    assert set(services[visible["id"]]) == {
        "id",
        "name",
        "duration_minutes",
        "price",
    }
    assert services[visible["id"]]["price"] == "120.00"
    assert services[hidden["id"]]["price"] is None

    professional_ids = {item["id"] for item in body["professionals"]}
    assert str(collaborator.user_id) in professional_ids
    assert str(owner.user_id) not in professional_ids
    for item in body["professionals"]:
        assert set(item) == {"id", "full_name"}

    raw = response.text
    for forbidden in ("score", "is_blocked", "cost", "phone", "email"):
        assert forbidden not in raw


async def test_invalid_magic_token_is_rejected(
    auth_client,
    tenant_users,
) -> None:
    response = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/context",
        params={"t": "token-inexistente"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Link inválido ou expirado"


async def test_cross_tenant_token_is_rejected(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    response = await auth_client.get(
        f"/api/v1/public/{auth_user.tenant_slug}/context",
        params={"t": magic},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Link inválido ou expirado"


async def test_public_availability_returns_only_free_slots(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    response = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/availability",
        params={
            "t": magic,
            "service_id": service["id"],
            "collaborator_id": str(collaborator.user_id),
            "date": DAY.isoformat(),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["available"] is True
    assert body["available_slots"][0] == "08:00"
    assert all(
        len(slot) == 5 and slot[2] == ":" for slot in body["available_slots"]
    )
    assert "Maria" not in response.text


async def test_public_booking_creates_scheduled_appointment_and_client(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )
    full_name = f"Novo Cliente {uuid4().hex[:6]}"

    response = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(13),
        full_name=full_name,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
        "id",
        "starts_at",
        "ends_at",
        "status",
        "service_name",
        "collaborator_name",
        "deposit_amount",
        "used_subscription",
    }
    assert body["status"] == "SCHEDULED"
    assert body["deposit_amount"] is None
    assert body["service_name"] == service["name"]
    assert body["collaborator_name"] == f"User {collaborator.role.value}"

    agenda = await auth_client.get(
        APPOINTMENTS,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert agenda.status_code == 200
    created = agenda.json()
    assert len(created) == 1
    assert created[0]["client_name"] == full_name
    assert created[0]["status"] == "SCHEDULED"

    clients = await auth_client.get(CLIENTS, headers=_auth(token))
    assert clients.status_code == 200
    assert any(item["full_name"] == full_name for item in clients.json())


async def test_public_booking_conflict_returns_409(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    first = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(14),
    )
    assert first.status_code == 201, first.text

    second = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(14),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "Horário indisponível"


async def test_blocked_client_gets_neutral_empty_availability_and_conflict(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    service = await _create_service(auth_client, token)

    blocked = await auth_client.patch(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(token),
        json={"is_blocked": True, "score": 5},
    )
    assert blocked.status_code == 200, blocked.text

    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        phone,
    )

    availability = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/availability",
        params={
            "t": magic,
            "service_id": service["id"],
            "collaborator_id": str(collaborator.user_id),
            "date": DAY.isoformat(),
        },
    )
    assert availability.status_code == 200
    assert availability.json()["available"] is False
    assert availability.json()["available_slots"] == []

    booking = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(15),
    )
    assert booking.status_code == 409
    detail = booking.json()["detail"]
    assert "recepção" in detail
    for forbidden in ("bloque", "score", "5"):
        assert forbidden not in detail.lower()


async def test_public_booking_requires_deposit_sets_pending(
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
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    response = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=_at(16),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING_DEPOSIT"
    assert body["deposit_amount"] == "30.00"


async def test_public_booking_requires_future_timezone_aware_start(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    _, magic = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        _phone(),
    )

    past = await _public_booking(
        auth_client,
        slug=tenant_users.tenant_slug,
        token=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        starts_at=datetime(2020, 1, 1, 10, tzinfo=TZ),
    )
    assert past.status_code == 422

    naive = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/appointments",
        params={"t": magic},
        json={
            "service_id": service["id"],
            "collaborator_id": str(collaborator.user_id),
            "starts_at": "2027-01-20T13:00:00",
            "full_name": "Cliente Público",
        },
    )
    assert naive.status_code == 422
