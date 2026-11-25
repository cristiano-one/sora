"""Engine e sessões assíncronas do SQLAlchemy (asyncpg)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    """Cria um engine assíncrono a partir de uma URL de conexão."""
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Cria a fábrica de sessões assíncronas para um engine."""
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


engine = create_engine(settings.database_url)
session_factory = create_session_factory(engine)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependência FastAPI que fornece uma sessão por requisição."""
    async with session_factory() as session:
        yield session
