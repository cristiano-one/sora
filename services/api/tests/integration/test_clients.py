"""Testes de clientes, score, LGPD, prontuário, anexos e auditoria."""

from uuid import UUID, uuid4

import pytest
from app.core.crypto import decrypt_text
from app.db.rls import set_tenant_context
from app.db.session import create_engine, create_session_factory
from app.models import AuditLog, MedicalRecord, UserRole
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

pytestmark = [pytest.mark.security, pytest.mark.integration]

CLIENTS = "/api/v1/clients"
LOGIN = "/api/v1/auth/login"
TENANTS = "/api/v1/tenants"


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


def _client_payload(suffix: str) -> dict[str, object]:
    return {
        "full_name": f"Cliente {suffix}",
        "phone": "(11) 91234-5678",
        "email": f"cliente-{suffix}@example.com",
        "birth_date": "1990-01-01",
    }


async def _create_client(auth_client, token: str, suffix: str) -> dict[str, object]:
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json=_client_payload(suffix),
    )
    assert response.status_code == 201
    return response.json()


async def _create_record(
    auth_client,
    token: str,
    client_id: object,
    *,
    notes: str = "Pele sensível",
) -> dict[str, object]:
    response = await auth_client.post(
        f"{CLIENTS}/{client_id}/records",
        headers=_auth(token),
        json={"title": "Avaliação", "notes": notes},
    )
    assert response.status_code == 201
    return response.json()


async def _audit_actions(database_urls, tenant_id) -> list[str]:
    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        rows = (
            await session.scalars(
                select(AuditLog.action).where(AuditLog.tenant_id == tenant_id)
            )
        ).all()
    await engine.dispose()
    return list(rows)


async def test_owner_creates_client(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])

    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])

    assert client["phone"] == "(11) 91234-5678"
    assert client["score"] == 100
    assert client["is_blocked"] is False


async def test_collaborator_sees_masked_phone(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    response = await auth_client.get(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(collab_token),
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "(11) 9****-5678"


async def test_collaborator_cannot_create_client(
    auth_client,
    tenant_users,
) -> None:
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    response = await auth_client.post(
        CLIENTS,
        headers=_auth(collab_token),
        json=_client_payload(uuid4().hex[:8]),
    )

    assert response.status_code == 403


async def test_score_event_updates_score(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])

    event = await auth_client.post(
        f"{CLIENTS}/{client['id']}/score-events",
        headers=_auth(owner_token),
        json={"rating": "NEGATIVE", "notes": "Atrasou 40 minutos"},
    )

    assert event.status_code == 201
    assert event.json()["rating"] == "NEGATIVE"
    assert event.json()["score_after"] == 90

    refreshed = await auth_client.get(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(owner_token),
    )
    assert refreshed.json()["score"] == 90


async def test_collaborator_can_add_score_event(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    collab_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )

    response = await auth_client.post(
        f"{CLIENTS}/{client['id']}/score-events",
        headers=_auth(collab_token),
        json={"rating": "POSITIVE", "notes": "Cliente pontual"},
    )

    assert response.status_code == 201
    assert response.json()["score_after"] == 100


async def test_consent_is_recorded(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])

    response = await auth_client.post(
        f"{CLIENTS}/{client['id']}/consents",
        headers=_auth(owner_token),
        json={
            "terms_version": "v1",
            "purposes": ["clinical_photos", "whatsapp_notices"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["terms_version"] == "v1"
    assert data["purposes"] == ["clinical_photos", "whatsapp_notices"]
    assert data["accepted_at"]


async def test_medical_record_encrypts_notes(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    record = await _create_record(auth_client, owner_token, client["id"])

    assert record["notes"] == "Pele sensível"

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        stored = await session.get(MedicalRecord, UUID(str(record["id"])))
        assert stored is not None
        assert stored.notes_encrypted != "Pele sensível"
        assert decrypt_text(stored.notes_encrypted) == "Pele sensível"
    await engine.dispose()


async def test_medical_record_list_audits(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    await _create_record(auth_client, owner_token, client["id"])

    listing = await auth_client.get(
        f"{CLIENTS}/{client['id']}/records",
        headers=_auth(owner_token),
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    actions = await _audit_actions(database_urls, tenant_users.tenant_id)
    assert "medical_record.create" in actions
    assert "medical_record.list" in actions


async def test_attachment_presign_and_url(
    auth_client,
    tenant_users,
    database_urls,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    record = await _create_record(auth_client, owner_token, client["id"])

    presign = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(owner_token),
        json={
            "filename": "antes-depois.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
        },
    )

    assert presign.status_code == 201
    data = presign.json()
    assert data["expires_in"] == 60
    assert "X-Amz-Expires=60" in data["upload_url"]

    url = await auth_client.get(
        f"{CLIENTS}/{client['id']}/records/{record['id']}"
        f"/attachments/{data['attachment_id']}/url",
        headers=_auth(owner_token),
    )

    assert url.status_code == 200
    assert url.json()["expires_in"] == 60
    assert "X-Amz-Expires=60" in url.json()["url"]

    actions = await _audit_actions(database_urls, tenant_users.tenant_id)
    assert "attachment.presign_upload" in actions
    assert "attachment.view_url" in actions


async def test_invalid_attachment_mime_is_rejected(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    record = await _create_record(auth_client, owner_token, client["id"])

    response = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(owner_token),
        json={
            "filename": "script.sh",
            "content_type": "text/plain",
            "size_bytes": 100,
        },
    )

    assert response.status_code == 422


async def test_oversized_attachment_is_rejected(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])
    record = await _create_record(auth_client, owner_token, client["id"])

    response = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(owner_token),
        json={
            "filename": "grande.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 11 * 1024 * 1024,
        },
    )

    assert response.status_code == 422


async def test_cross_tenant_client_returns_404(
    auth_client,
    tenant_users,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])

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
        f"{CLIENTS}/{client['id']}",
        headers=_auth(token_b),
    )
    patch_response = await auth_client.patch(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(token_b),
        json={"full_name": "Invasor"},
    )

    assert get_response.status_code == 404
    assert patch_response.status_code == 404


async def test_admin_can_block_client(auth_client, tenant_users) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token, uuid4().hex[:8])

    response = await auth_client.patch(
        f"{CLIENTS}/{client['id']}",
        headers=_auth(owner_token),
        json={"is_blocked": True},
    )

    assert response.status_code == 200
    assert response.json()["is_blocked"] is True


async def test_audit_log_is_immutable(app_session, tenant_users) -> None:
    await set_tenant_context(app_session, tenant_users.tenant_id)

    with pytest.raises(DBAPIError):
        await app_session.execute(text("UPDATE audit_logs SET action = 'x'"))
    await app_session.rollback()

    await set_tenant_context(app_session, tenant_users.tenant_id)
    with pytest.raises(DBAPIError):
        await app_session.execute(text("DELETE FROM audit_logs"))
    await app_session.rollback()
