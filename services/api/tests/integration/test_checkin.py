"""Check-in digital: link, marcação e idempotência."""

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
CHECKIN = "/api/v1/public/checkin"


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


async def _appointment(auth_client, tenant_users) -> dict:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    suffix = uuid4().hex[:6]
    service = await auth_client.post(
        SERVICES,
        headers=_auth(token),
        json={
            "name": f"Checkin {suffix}",
            "duration_minutes": 30,
            "buffer_minutes": 0,
            "price": "80.00",
            "cost": "10.00",
        },
    )
    assert service.status_code == 201
    client = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": "Cliente Checkin",
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
            "collaborator_id": str(
                tenant_users.users[UserRole.COLLABORATOR].user_id
            ),
            "starts_at": datetime.combine(
                DAY,
                time(9),
                tzinfo=TZ,
            ).isoformat(),
        },
    )
    assert appointment.status_code == 201, appointment.text
    return {"token": token, "appointment": appointment.json()}


async def test_public_checkin_marks_arrival(
    auth_client,
    tenant_users,
) -> None:
    data = await _appointment(auth_client, tenant_users)
    link = await auth_client.post(
        f"{APPOINTMENTS}/{data['appointment']['id']}/checkin-link",
        headers=_auth(data["token"]),
    )
    assert link.status_code == 200, link.text
    assert f"/checkin/{tenant_users.tenant_slug}/" in link.json()["url"]

    checkin_token = link.json()["token"]
    before = await auth_client.get(
        f"{CHECKIN}/{tenant_users.tenant_slug}/{checkin_token}"
    )
    assert before.status_code == 200, before.text
    assert before.json()["can_checkin"] is True
    assert before.json()["checked_in_at"] is None
    assert before.json()["client_name"] == "Cliente"

    marked = await auth_client.post(
        f"{CHECKIN}/{tenant_users.tenant_slug}/{checkin_token}"
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["checked_in_at"] is not None
    assert marked.json()["can_checkin"] is False

    again = await auth_client.post(
        f"{CHECKIN}/{tenant_users.tenant_slug}/{checkin_token}"
    )
    assert again.status_code == 200
    assert again.json()["checked_in_at"] == marked.json()["checked_in_at"]

    internal = await auth_client.get(
        f"{APPOINTMENTS}/{data['appointment']['id']}",
        headers=_auth(data["token"]),
    )
    assert internal.status_code == 200
    assert internal.json()["checked_in_at"] is not None

    invalid = await auth_client.get(
        f"{CHECKIN}/{tenant_users.tenant_slug}/token-invalido"
    )
    assert invalid.status_code == 404


async def test_checkin_link_requires_scope_and_slug_isolation(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    data = await _appointment(auth_client, tenant_users)
    collaborator_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    allowed = await auth_client.post(
        f"{APPOINTMENTS}/{data['appointment']['id']}/checkin-link",
        headers=_auth(collaborator_token),
    )
    assert allowed.status_code == 200

    other_token = await _login(auth_client, auth_user)
    forbidden = await auth_client.post(
        f"{APPOINTMENTS}/{data['appointment']['id']}/checkin-link",
        headers=_auth(other_token),
    )
    assert forbidden.status_code == 404

    link = await auth_client.post(
        f"{APPOINTMENTS}/{data['appointment']['id']}/checkin-link",
        headers=_auth(data["token"]),
    )
    wrong_slug = await auth_client.get(
        f"{CHECKIN}/{auth_user.tenant_slug}/{link.json()['token']}"
    )
    assert wrong_slug.status_code == 404
