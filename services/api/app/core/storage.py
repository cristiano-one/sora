"""Porta de storage privado e adaptador S3/MinIO com URLs pré-assinadas."""

from typing import Protocol

import boto3
from botocore.config import Config

from app.core.config import settings


class StoragePort(Protocol):
    """Contrato mínimo de storage para prontuários."""

    def presign_upload(self, key: str, content_type: str, expires_in: int) -> str:
        """Retorna uma URL pré-assinada de upload (PUT)."""
        ...

    def presign_download(self, key: str, expires_in: int) -> str:
        """Retorna uma URL pré-assinada de leitura (GET)."""
        ...


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


_storage: StoragePort | None = None


def get_storage() -> StoragePort:
    """Dependência FastAPI do storage privado (singleton preguiçoso)."""
    global _storage
    if _storage is None:
        _storage = S3Storage()
    return _storage
