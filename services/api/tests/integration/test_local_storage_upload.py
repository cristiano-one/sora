"""Fluxo HTTP de upload/download/exclusão com o storage local assinado."""

from pathlib import Path
from uuid import uuid4

import pytest
from app.core.storage import LocalStorage, get_storage
from app.main import app
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

CLIENTS = "/api/v1/clients"
LOGIN = "/api/v1/auth/login"


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


async def _create_client(auth_client, token: str) -> dict:
    response = await auth_client.post(
        CLIENTS,
        headers=_auth(token),
        json={
            "full_name": f"Anexo Local {uuid4().hex[:6]}",
            "phone": f"119{uuid4().int % 10**8:08d}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_record(auth_client, token: str, client_id: str) -> dict:
    response = await auth_client.post(
        f"{CLIENTS}/{client_id}/records",
        headers=_auth(token),
        json={"title": "Avaliação", "notes": "Notas clínicas"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def local_storage(tmp_path: Path):
    storage = LocalStorage(root=tmp_path, signing_secret="integration-secret")
    app.dependency_overrides[get_storage] = lambda: storage
    try:
        yield storage
    finally:
        app.dependency_overrides.pop(get_storage, None)


async def test_local_upload_download_and_delete(
    auth_client,
    tenant_users,
    local_storage: LocalStorage,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, token)
    record = await _create_record(auth_client, token, client["id"])

    presign = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(token),
        json={
            "filename": "foto.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 12,
        },
    )
    assert presign.status_code == 201, presign.text
    data = presign.json()
    assert data["upload_url"].startswith("/api/v1/storage/upload/")

    upload = await auth_client.put(
        data["upload_url"],
        content=b"fake-jpeg-12",
        headers={"Content-Type": "image/jpeg"},
    )
    assert upload.status_code == 204, upload.text

    url = await auth_client.get(
        f"{CLIENTS}/{client['id']}/records/{record['id']}"
        f"/attachments/{data['attachment_id']}/url",
        headers=_auth(token),
    )
    assert url.status_code == 200
    assert url.json()["url"].startswith("/api/v1/storage/download/")

    download = await auth_client.get(url.json()["url"])
    assert download.status_code == 200
    assert download.content == b"fake-jpeg-12"
    assert download.headers["content-type"].startswith("image/jpeg")
    assert "inline" in download.headers["content-disposition"]

    deleted = await auth_client.delete(
        f"{CLIENTS}/{client['id']}/records/{record['id']}"
        f"/attachments/{data['attachment_id']}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204, deleted.text

    gone = await auth_client.get(url.json()["url"])
    assert gone.status_code == 404


async def test_local_upload_rejects_wrong_content_type(
    auth_client,
    tenant_users,
    local_storage: LocalStorage,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, token)
    record = await _create_record(auth_client, token, client["id"])
    presign = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(token),
        json={
            "filename": "foto.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 12,
        },
    )
    assert presign.status_code == 201

    upload = await auth_client.put(
        presign.json()["upload_url"],
        content=b"%PDF-1.7",
        headers={"Content-Type": "application/pdf"},
    )
    assert upload.status_code == 422


async def test_local_upload_rejects_tampered_token(
    auth_client,
    local_storage: LocalStorage,
) -> None:
    upload = await auth_client.put(
        "/api/v1/storage/upload/eyJhIjoidSJ9.AAAA",
        content=b"x",
        headers={"Content-Type": "image/jpeg"},
    )
    assert upload.status_code == 404


async def test_collaborator_cannot_delete_attachment(
    auth_client,
    tenant_users,
    local_storage: LocalStorage,
) -> None:
    owner_token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    client = await _create_client(auth_client, owner_token)
    record = await _create_record(auth_client, owner_token, client["id"])
    presign = await auth_client.post(
        f"{CLIENTS}/{client['id']}/records/{record['id']}/attachments/presign",
        headers=_auth(owner_token),
        json={
            "filename": "foto.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 4,
        },
    )
    assert presign.status_code == 201
    attachment_id = presign.json()["attachment_id"]

    collaborator_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    deleted = await auth_client.delete(
        f"{CLIENTS}/{client['id']}/records/{record['id']}"
        f"/attachments/{attachment_id}",
        headers=_auth(collaborator_token),
    )
    assert deleted.status_code == 403
