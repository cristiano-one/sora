"""Endpoints de health check (liveness)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Retorna o status da aplicação (liveness)."""
    return {"status": "ok"}
