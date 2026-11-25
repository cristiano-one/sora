"""Pagamento Pix mock: confirmação, posse, expiração e idempotência."""

from datetime import UTC, datetime, time, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import settings
from app.db.rls import set_tenant_context
from app.models import Appointment, PaymentIntent, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.security, pytest.mark.integration]

TZ = ZoneInfo("America/Sao_Paulo")
DAY = datetime.now(TZ).date() + timedelta(days=1)
LOGIN = "/api/v1/auth/login"
SERVICES = "/api/v1/services"
CLIENTS = "/api/v1/clients"
APPOINTMENTS = "/api/v1/appointments"


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


async def _create_service(auth_client, token: str) -> dict[str, object]:
    response = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Serviço {uuid4().hex[:6]}",
            "duration_minutes": 60,
            "buffer_minutes": 0,
            "price": "120.00",
            "cost": "20.00",
            "requires_deposit": True,
            "deposit_amount": "30.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_client(
    auth_client,
    token: str,
    *,
    phone: str,
) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Cliente {suffix}",
            "phone": phone,
            "email": f"cliente-{suffix}@example.com",
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


async def _public_book(
    auth_client,
    *,
    slug: str,
    magic: str,
    service_id: object,
    collaborator_id: object,
    full_name: str,
) -> dict[str, object]:
    response = await auth_client.post(
        f"/api/v1/public/{slug}/appointments",
        params={"t": magic},
        json={
            "service_id": service_id,
            "collaborator_id": str(collaborator_id),
            "starts_at": _at(10).isoformat(),
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_public_deposit_payment_confirms_appointment(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)

    booked = await _public_book(
        auth_client,
        slug=tenant_users.tenant_slug,
        magic=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        full_name=client["full_name"],
    )
    assert booked["status"] == "PENDING_DEPOSIT"
    payment = booked["payment"]
    assert payment is not None
    assert payment["status"] == "PENDING"

    confirmed = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/"
        f"{payment['id']}/mock-confirm",
        params={"t": magic},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "PAID"
    assert body["appointment_status"] == "CONFIRMED"

    agenda = await auth_client.get(
        APPOINTMENTS,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert agenda.status_code == 200
    appointment = agenda.json()[0]
    assert appointment["id"] == booked["id"]
    assert appointment["status"] == "CONFIRMED"

    again = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/"
        f"{payment['id']}/mock-confirm",
        params={"t": magic},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "PAID"

    status = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/{payment['id']}",
        params={"t": magic},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "PAID"


async def test_cross_client_cannot_read_or_confirm_payment(
    auth_client,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    phone_a = _phone()
    phone_b = _phone()
    client_a = await _create_client(auth_client, token, phone=phone_a)
    await _create_client(auth_client, token, phone=phone_b)
    magic_a = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        phone_a,
    )
    magic_b = await _magic_link(
        auth_client,
        tenant_users.tenant_slug,
        phone_b,
    )
    booked = await _public_book(
        auth_client,
        slug=tenant_users.tenant_slug,
        magic=magic_a,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        full_name=client_a["full_name"],
    )
    payment_id = booked["payment"]["id"]

    read = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/{payment_id}",
        params={"t": magic_b},
    )
    assert read.status_code == 404

    confirm = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/"
        f"{payment_id}/mock-confirm",
        params={"t": magic_b},
    )
    assert confirm.status_code == 404

    owner_view = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/{payment_id}",
        params={"t": magic_a},
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["status"] == "PENDING"


async def test_expired_payment_frees_appointment(
    auth_client,
    app_session: AsyncSession,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)
    booked = await _public_book(
        auth_client,
        slug=tenant_users.tenant_slug,
        magic=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        full_name=client["full_name"],
    )
    payment_id = UUID(booked["payment"]["id"])
    appointment_id = UUID(booked["id"])

    await set_tenant_context(app_session, tenant_users.tenant_id)
    payment = await app_session.get(PaymentIntent, payment_id)
    appointment = await app_session.get(Appointment, appointment_id)
    assert payment is not None
    assert appointment is not None
    past = datetime.now(UTC) - timedelta(minutes=1)
    payment.expires_at = past
    appointment.deposit_expires_at = past
    await app_session.commit()

    confirm = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/"
        f"{payment_id}/mock-confirm",
        params={"t": magic},
    )
    assert confirm.status_code == 409
    assert confirm.json()["detail"] == "Pagamento expirado"

    status = await auth_client.get(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/{payment_id}",
        params={"t": magic},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "EXPIRED"

    agenda = await auth_client.get(
        APPOINTMENTS,
        headers=_auth(token),
        params={"from_date": DAY.isoformat(), "to_date": DAY.isoformat()},
    )
    assert agenda.status_code == 200
    assert agenda.json()[0]["status"] == "EXPIRED"

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
    assert "10:00" in availability.json()["available_slots"]


async def test_mock_confirm_disabled_for_non_mock_provider(
    auth_client,
    monkeypatch,
    tenant_users,
) -> None:
    owner = tenant_users.users[UserRole.OWNER]
    collaborator = tenant_users.users[UserRole.COLLABORATOR]
    token = await _login(auth_client, owner)
    service = await _create_service(auth_client, token)
    phone = _phone()
    client = await _create_client(auth_client, token, phone=phone)
    magic = await _magic_link(auth_client, tenant_users.tenant_slug, phone)
    booked = await _public_book(
        auth_client,
        slug=tenant_users.tenant_slug,
        magic=magic,
        service_id=service["id"],
        collaborator_id=collaborator.user_id,
        full_name=client["full_name"],
    )
    payment_id = booked["payment"]["id"]

    monkeypatch.setattr(settings, "payment_provider", "real")
    confirm = await auth_client.post(
        f"/api/v1/public/{tenant_users.tenant_slug}/payments/"
        f"{payment_id}/mock-confirm",
        params={"t": magic},
    )
    assert confirm.status_code == 404
