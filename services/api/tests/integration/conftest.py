"""Fixtures de integração com PostgreSQL e Redis reais (testcontainers)."""

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import boto3
import httpx
import pytest
from alembic import command
from alembic.config import Config
from app.core.auth.security import hash_password
from app.core.config import settings
from app.core.redis import create_redis, get_redis
from app.core.storage import S3Storage, get_storage
from app.db.session import create_engine, create_session_factory, get_session
from app.main import app
from app.models import Tenant, User, UserRole
from moto import mock_aws
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

API_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = API_DIR.parents[1]
RLS_INIT_SCRIPT = REPO_ROOT / "infra" / "postgres" / "init" / "01-init-rls-roles.sh"


@dataclass(frozen=True)
class SeededData:
    """IDs criados para os testes de isolamento multi-tenant."""

    tenant_a: UUID
    tenant_b: UUID
    user_a: UUID
    user_b: UUID


@dataclass(frozen=True)
class AuthUser:
    """Credenciais e IDs de um usuário criado para os testes de auth."""

    tenant_id: UUID
    tenant_slug: str
    user_id: UUID
    email: str
    password: str
    role: UserRole


@dataclass(frozen=True)
class TenantUsers:
    """Tenant com um usuário para cada papel RBAC."""

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    users: dict[UserRole, AuthUser]


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """Sobe um PostgreSQL 16 real com o role de runtime (NOBYPASSRLS)."""
    container = PostgresContainer(
        "postgres:16-alpine",
        username="sora",
        password="sora_test_owner",
        dbname="sora_test",
    )
    container.with_env("POSTGRES_APP_USER", "sora_app")
    container.with_env("POSTGRES_APP_PASSWORD", "sora_test_app")
    container.with_volume_mapping(
        str(RLS_INIT_SCRIPT),
        "/docker-entrypoint-initdb.d/01-init-rls-roles.sh",
        "ro",
    )
    with container:
        yield container


@pytest.fixture(scope="session")
def database_urls(postgres_container) -> dict[str, str]:
    """URLs asyncpg do owner (migrations) e do role RLS (runtime)."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    return {
        "owner": f"postgresql+asyncpg://sora:sora_test_owner@{host}:{port}/sora_test",
        "app": f"postgresql+asyncpg://sora_app:sora_test_app@{host}:{port}/sora_test",
    }


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    """Sobe um Redis 7 real para os testes de sessão/tokens."""
    container = RedisContainer("redis:7-alpine")
    with container:
        yield container


@pytest.fixture(scope="session")
def redis_url(redis_container) -> str:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def s3_mock() -> Iterator[None]:
    """Ativa o mock do S3 (moto) para os testes de anexos."""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket="sora-private"
        )
        yield


@pytest.fixture
def test_storage(s3_mock, monkeypatch) -> S3Storage:
    """Storage S3 apontando para o moto (sem depender do MinIO externo)."""
    monkeypatch.setattr(settings, "storage_endpoint", None)
    monkeypatch.setattr(settings, "storage_access_key_id", "testing")
    monkeypatch.setattr(settings, "storage_secret_access_key", "testing")
    return S3Storage(bucket="sora-private", region="us-east-1")


@pytest.fixture(scope="session")
def migrated_database(database_urls) -> Iterator[None]:
    """Aplica todas as migrations Alembic no banco de teste (uma vez por sessão)."""
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_urls["owner"])
    command.upgrade(config, "head")
    yield


@pytest.fixture
async def app_engine(migrated_database, database_urls) -> AsyncIterator[AsyncEngine]:
    """Engine conectado com o role sora_app (NOBYPASSRLS)."""
    engine = create_engine(database_urls["app"])
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_session(app_engine) -> AsyncIterator[AsyncSession]:
    """Sessão do role de runtime; qualquer escrita é revertida ao final."""
    factory = create_session_factory(app_engine)
    async with factory() as session:
        yield session


@pytest.fixture
async def test_redis(redis_url) -> AsyncIterator[Redis]:
    """Cliente Redis do teste, com o banco limpo antes de cada caso."""
    client = create_redis(redis_url)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest.fixture
async def auth_client(
    app_engine,
    test_redis,
    test_storage,
) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP com banco/Redis/storage de teste injetados."""

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        factory = create_session_factory(app_engine)
        async with factory() as session:
            yield session

    async def override_get_redis() -> Redis:
        return test_redis

    def override_get_storage() -> S3Storage:
        return test_storage

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_storage] = override_get_storage
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
async def seeded(migrated_database, database_urls) -> SeededData:
    """Cria dois tenants e um OWNER em cada um, usando o owner (bypass RLS)."""
    suffix = uuid4().hex[:8]
    data = SeededData(
        tenant_a=uuid4(),
        tenant_b=uuid4(),
        user_a=uuid4(),
        user_b=uuid4(),
    )

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add_all(
            [
                Tenant(id=data.tenant_a, name="Clínica A", slug=f"clinica-a-{suffix}"),
                Tenant(id=data.tenant_b, name="Clínica B", slug=f"clinica-b-{suffix}"),
                User(
                    id=data.user_a,
                    tenant_id=data.tenant_a,
                    email=f"owner-a-{suffix}@example.com",
                    hashed_password="x",
                    full_name="Owner A",
                    role=UserRole.OWNER,
                ),
                User(
                    id=data.user_b,
                    tenant_id=data.tenant_b,
                    email=f"owner-b-{suffix}@example.com",
                    hashed_password="x",
                    full_name="Owner B",
                    role=UserRole.OWNER,
                ),
            ]
        )
        await session.commit()
    await engine.dispose()

    return data


@pytest.fixture
async def auth_user(migrated_database, database_urls) -> AuthUser:
    """Cria um tenant e um OWNER com senha real (hash Argon2)."""
    suffix = uuid4().hex[:8]
    password = "senha-forte-123"
    data = AuthUser(
        tenant_id=uuid4(),
        tenant_slug=f"clinica-auth-{suffix}",
        user_id=uuid4(),
        email=f"owner-auth-{suffix}@example.com",
        password=password,
        role=UserRole.OWNER,
    )

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(
            Tenant(id=data.tenant_id, name="Clínica Auth", slug=data.tenant_slug)
        )
        session.add(
            User(
                id=data.user_id,
                tenant_id=data.tenant_id,
                email=data.email,
                hashed_password=hash_password(password),
                full_name="Owner Auth",
                role=data.role,
            )
        )
        await session.commit()
    await engine.dispose()

    return data


@pytest.fixture
async def tenant_users(migrated_database, database_urls) -> TenantUsers:
    """Cria um tenant com OWNER, ADMIN e COLLABORATOR (senha real)."""
    suffix = uuid4().hex[:8]
    tenant_id = uuid4()
    tenant_name = "Clínica RBAC"
    tenant_slug = f"clinica-rbac-{suffix}"
    password = "senha-forte-123"
    users: dict[UserRole, AuthUser] = {}

    engine = create_engine(database_urls["owner"])
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(Tenant(id=tenant_id, name=tenant_name, slug=tenant_slug))
        for role in (UserRole.OWNER, UserRole.ADMIN, UserRole.COLLABORATOR):
            user_id = uuid4()
            email = f"{role.value.lower()}-{suffix}@example.com"
            is_collaborator = role == UserRole.COLLABORATOR
            session.add(
                User(
                    id=user_id,
                    tenant_id=tenant_id,
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=f"User {role.value}",
                    role=role,
                    commission_percentage=(
                        Decimal("40.00") if is_collaborator else None
                    ),
                    commission_fixed=(
                        Decimal("5.00") if is_collaborator else None
                    ),
                )
            )
            users[role] = AuthUser(
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                user_id=user_id,
                email=email,
                password=password,
                role=role,
            )
        await session.commit()
    await engine.dispose()

    return TenantUsers(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        tenant_slug=tenant_slug,
        users=users,
    )
