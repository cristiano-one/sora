"""Storage local assinado: assinatura, expiração, path traversal e arquivos."""

from pathlib import Path

import pytest
from app.core.storage import (
    LocalStorage,
    StorageTokenError,
    StorageTokenExpired,
)

pytestmark = pytest.mark.security


def _storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(root=tmp_path, signing_secret="test-secret")


def test_upload_and_download_tokens_round_trip(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    key = "tenant/abc/clients/1/records/2/3/foto.jpg"

    upload = storage.presign_upload(key, "image/jpeg", 60)
    assert upload.startswith("/api/v1/storage/upload/")
    upload_grant = storage.verify_upload(upload.rsplit("/", 1)[-1])
    assert upload_grant.key == key
    assert upload_grant.content_type == "image/jpeg"
    assert upload_grant.max_size == 10 * 1024 * 1024

    payload = b"\xff\xd8\xff fake jpeg"
    storage.save(key, payload)
    assert storage.read(key) == payload
    assert (tmp_path / key).stat().st_mode & 0o777 == 0o600

    download = storage.presign_download(key, 60)
    assert download.startswith("/api/v1/storage/download/")
    download_grant = storage.verify_download(download.rsplit("/", 1)[-1])
    assert download_grant.key == key


def test_expired_token_is_rejected(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    token = storage.presign_download("tenant/a/file.jpg", -1).rsplit("/", 1)[-1]

    with pytest.raises(StorageTokenExpired):
        storage.verify_download(token)


def test_tampered_token_is_rejected(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    token = storage.presign_download("tenant/a/file.jpg", 60).rsplit("/", 1)[-1]
    body, _signature = token.split(".", 1)

    with pytest.raises(StorageTokenError):
        storage.verify_download(f"{body}.AAAA")


def test_upload_token_cannot_be_used_for_download(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    token = storage.presign_upload("tenant/a/file.jpg", "image/jpeg", 60)
    token = token.rsplit("/", 1)[-1]

    with pytest.raises(StorageTokenError):
        storage.verify_download(token)


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    token = storage.presign_download("../../etc/passwd", 60)
    token = token.rsplit("/", 1)[-1]
    grant = storage.verify_download(token)

    with pytest.raises(StorageTokenError):
        storage.path_for_read(grant.key)


def test_delete_is_idempotent(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    key = "tenant/a/file.jpg"
    storage.save(key, b"conteudo")

    storage.delete(key)
    storage.delete(key)

    assert not (tmp_path / key).exists()
