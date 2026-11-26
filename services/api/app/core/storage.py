"""Porta de storage privado com adaptadores S3/MinIO e local assinado."""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config

from app.core.config import BASE_DIR, settings

_LOCAL_SIGNING_CONTEXT = b"sora-local-storage-v1"
_TOKEN_MAX_LENGTH = 4096


class StoragePort(Protocol):
    """Contrato mínimo de storage para prontuários."""

    def presign_upload(self, key: str, content_type: str, expires_in: int) -> str:
        """Retorna uma URL pré-assinada de upload (PUT)."""
        ...

    def presign_download(self, key: str, expires_in: int) -> str:
        """Retorna uma URL pré-assinada de leitura (GET)."""
        ...

    def delete(self, key: str) -> None:
        """Remove o objeto privado (idempotente)."""
        ...


class StorageTokenError(Exception):
    """Token de storage inválido, adulterado ou fora do escopo."""


class StorageTokenExpired(StorageTokenError):
    """Token de storage expirado."""


@dataclass(frozen=True)
class StorageGrant:
    """Conteúdo validado de um token de upload/download."""

    key: str
    action: str
    content_type: str | None
    max_size: int | None


class S3Storage:
    """Adaptador S3-compatível (AWS S3 / Cloudflare R2 / MinIO)."""

    def __init__(self, *, bucket: str | None = None, region: str | None = None) -> None:
        self.bucket = bucket or settings.storage_bucket
        self._client = boto3.client(
            "s3",
            region_name=region or settings.storage_region,
            endpoint_url=settings.storage_endpoint or None,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    def presign_upload(self, key: str, content_type: str, expires_in: int) -> str:
        return str(
            self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
        )

    def presign_download(self, key: str, expires_in: int) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)


class LocalStorage:
    """Storage em disco privado com URLs assinadas pela própria API.

    Indicado para desenvolvimento local e preview sem MinIO/S3. As URLs são
    relativas (``/api/v1/storage/...``) para funcionar tanto no proxy do web
    quanto no app mobile, que resolve a URL contra ``API_URL``.
    """

    def __init__(
        self,
        *,
        root: Path | str | None = None,
        signing_secret: str | None = None,
    ) -> None:
        configured = root or settings.storage_local_path
        path = Path(configured).expanduser()
        self.root = path if path.is_absolute() else BASE_DIR / path
        self._secret = (
            signing_secret.encode()
            if signing_secret is not None
            else hmac.new(
                settings.jwt_secret_key.encode(),
                _LOCAL_SIGNING_CONTEXT,
                hashlib.sha256,
            ).digest()
        )

    # ------------------------------------------------------------------
    # URLs assinadas
    # ------------------------------------------------------------------
    def presign_upload(self, key: str, content_type: str, expires_in: int) -> str:
        token = self._sign(
            {
                "a": "u",
                "k": key,
                "c": content_type,
                "m": settings.storage_max_attachment_bytes,
                "e": int(time.time()) + expires_in,
            }
        )
        return f"{settings.api_v1_prefix}/storage/upload/{token}"

    def presign_download(self, key: str, expires_in: int) -> str:
        token = self._sign(
            {
                "a": "d",
                "k": key,
                "e": int(time.time()) + expires_in,
            }
        )
        return f"{settings.api_v1_prefix}/storage/download/{token}"

    def _sign(self, payload: dict[str, object]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        signature = hmac.new(
            self._secret,
            body.encode(),
            hashlib.sha256,
        ).digest()
        encoded = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{body}.{encoded}"

    def _verify(self, token: str, *, action: str) -> StorageGrant:
        if not token or len(token) > _TOKEN_MAX_LENGTH or token.count(".") != 1:
            raise StorageTokenError("token inválido")
        body, signature = token.split(".", 1)
        expected = hmac.new(
            self._secret,
            body.encode(),
            hashlib.sha256,
        ).digest()
        try:
            provided = _b64decode(signature)
        except ValueError as exc:
            raise StorageTokenError("token inválido") from exc
        if not hmac.compare_digest(expected, provided):
            raise StorageTokenError("assinatura inválida")
        try:
            payload = json.loads(_b64decode(body))
        except (ValueError, json.JSONDecodeError) as exc:
            raise StorageTokenError("payload inválido") from exc
        if not isinstance(payload, dict):
            raise StorageTokenError("payload inválido")

        if payload.get("a") != action:
            raise StorageTokenError("ação inválida")
        key = payload.get("k")
        expiry = payload.get("e")
        if not isinstance(key, str) or not key or "\x00" in key:
            raise StorageTokenError("chave inválida")
        if not isinstance(expiry, int) or isinstance(expiry, bool):
            raise StorageTokenError("validade inválida")
        if expiry < int(time.time()):
            raise StorageTokenExpired("token expirado")

        content_type = payload.get("c")
        max_size = payload.get("m")
        return StorageGrant(
            key=key,
            action=action,
            content_type=content_type if isinstance(content_type, str) else None,
            max_size=max_size if isinstance(max_size, int) else None,
        )

    def verify_upload(self, token: str) -> StorageGrant:
        return self._verify(token, action="u")

    def verify_download(self, token: str) -> StorageGrant:
        return self._verify(token, action="d")

    # ------------------------------------------------------------------
    # Arquivos
    # ------------------------------------------------------------------
    def _path_for(self, key: str) -> Path:
        root = self.root.resolve()
        candidate = (root / key).resolve()
        if candidate == root or root not in candidate.parents:
            raise StorageTokenError("chave fora do diretório permitido")
        return candidate

    def save(self, key: str, data: bytes) -> None:
        """Grava o objeto privado, criando diretórios com permissão restrita."""
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_name(f".{path.name}.part")
        temporary.write_bytes(data)
        temporary.chmod(0o600)
        temporary.replace(path)

    def read(self, key: str) -> bytes:
        path = self._path_for(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        path.unlink(missing_ok=True)
        parent = path.parent
        root = self.root.resolve()
        while parent != root and root in parent.parents:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def path_for_read(self, key: str) -> Path:
        path = self._path_for(key)
        if not path.is_file():
            raise StorageTokenError("arquivo inexistente")
        return path


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as exc:
        raise ValueError("base64 inválido") from exc


_storage: StoragePort | None = None


def build_storage() -> StoragePort:
    """Cria o adaptador conforme ``STORAGE_PROVIDER``."""
    provider = settings.storage_provider.strip().lower()
    if provider == "local":
        return LocalStorage()
    return S3Storage()


def get_storage() -> StoragePort:
    """Dependência FastAPI do storage privado (singleton preguiçoso)."""
    global _storage
    if _storage is None:
        _storage = build_storage()
    return _storage
