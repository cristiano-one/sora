"""Cliente Redis assíncrono e helpers de chaves multi-tenant."""

from typing import cast
from uuid import UUID

from fastapi import Request
from redis.asyncio import Redis


def create_redis(url: str) -> Redis:
    """Cria um cliente Redis assíncrono com respostas em texto."""
    return cast(Redis, Redis.from_url(url, decode_responses=True))


def tenant_key(tenant_id: UUID, *parts: str) -> str:
    """Monta uma chave Redis sempre prefixada pelo tenant (Zero-Leak)."""
    return ":".join(("tenant", str(tenant_id), *parts))


async def get_redis(request: Request) -> Redis:
    """Dependência FastAPI que fornece o cliente Redis criado no lifespan."""
    return cast(Redis, request.app.state.redis)
