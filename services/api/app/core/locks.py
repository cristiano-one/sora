"""Locks distribuídos no Redis (agenda anti-double-booking)."""

from collections.abc import Awaitable
from typing import cast
from uuid import uuid4

from redis.asyncio import Redis

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


async def acquire_lock(
    redis: Redis,
    key: str,
    *,
    ttl_seconds: int = 10,
) -> str | None:
    """Tenta adquirir o lock; retorna o token ou None se ocupado."""
    token = uuid4().hex
    acquired = await redis.set(key, token, nx=True, ex=ttl_seconds)
    return token if acquired else None


async def release_lock(redis: Redis, key: str, token: str) -> None:
    """Libera o lock apenas se o token ainda for o dono."""
    await cast(
        Awaitable[object],
        redis.eval(_RELEASE_SCRIPT, 1, key, token),
    )
