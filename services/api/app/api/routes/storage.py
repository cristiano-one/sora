"""Upload/download privados com URLs assinadas pelo storage local."""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from app.core.storage import (
    LocalStorage,
    StorageGrant,
    StorageTokenError,
    StorageTokenExpired,
    get_storage,
)

router = APIRouter(prefix="/storage", tags=["storage"])

_MAX_FILENAME = 180


def _local_storage(storage: object) -> LocalStorage:
    if not isinstance(storage, LocalStorage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage local não habilitado",
        )
    return storage


def _grant_or_error(
    token: str,
    storage: LocalStorage,
    *,
    action: str,
) -> StorageGrant:
    try:
        if action == "u":
            return storage.verify_upload(token)
        return storage.verify_download(token)
    except StorageTokenExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="URL expirada",
        ) from exc
    except StorageTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL inválida",
        ) from exc


def _normalize_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _safe_filename(key: str) -> str:
    name = Path(key).name or "arquivo"
    clean = "".join(
        char for char in name if char.isprintable() and char not in '"\\'
    )
    return (clean or "arquivo")[:_MAX_FILENAME]


@router.put(
    "/upload/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Recebe o upload de uma URL assinada",
)
async def upload_endpoint(
    token: str,
    request: Request,
    storage: object = Depends(get_storage),
) -> Response:
    local = _local_storage(storage)
    grant = _grant_or_error(token, local, action="u")
    if grant.content_type is None or grant.max_size is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL inválida",
        )

    declared = _normalize_content_type(request.headers.get("content-type"))
    if declared != grant.content_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de arquivo divergente",
        )

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > grant.max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Arquivo acima do limite",
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content-Length inválido",
            ) from exc

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > grant.max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Arquivo acima do limite",
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo vazio",
        )

    try:
        local.save(grant.key, data)
    except StorageTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL inválida",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao persistir anexo",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/download/{token}",
    summary="Baixa um anexo por URL assinada",
)
def download_endpoint(
    token: str,
    storage: object = Depends(get_storage),
) -> FileResponse:
    local = _local_storage(storage)
    grant = _grant_or_error(token, local, action="d")
    try:
        path = local.path_for_read(grant.key)
    except StorageTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não encontrado",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não encontrado",
        ) from exc

    filename = _safe_filename(grant.key)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
