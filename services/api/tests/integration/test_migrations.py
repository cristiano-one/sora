"""Valida migrations Alembic (upgrade e downgrade) em um banco isolado."""

import asyncio
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

API_DIR = Path(__file__).resolve().parents[2]
MIGRATION_DB_NAME = "sora_migrations_test"

pytestmark = pytest.mark.integration


async def _connect(owner_url: str, *, database: str) -> asyncpg.Connection:
    url = make_url(owner_url)
    return await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database=database,
    )


async def _create_database(owner_url: str) -> None:
    connection = await _connect(owner_url, database="postgres")
    try:
        await connection.execute(
            "DROP DATABASE IF EXISTS sora_migrations_test WITH (FORCE)"
        )
        await connection.execute("CREATE DATABASE sora_migrations_test")
    finally:
        await connection.close()


async def _drop_database(owner_url: str) -> None:
    connection = await _connect(owner_url, database="postgres")
    try:
        await connection.execute(
            "DROP DATABASE IF EXISTS sora_migrations_test WITH (FORCE)"
        )
    finally:
        await connection.close()


async def _schema(owner_url: str) -> tuple[set[str], set[str], set[str]]:
    connection = await _connect(owner_url, database=MIGRATION_DB_NAME)
    try:
        tables = await connection.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        enums = await connection.fetch("SELECT typname FROM pg_type WHERE typtype = 'e'")
        functions = await connection.fetch(
            "SELECT proname FROM pg_proc WHERE proname = 'resolve_tenant_id_by_slug'"
        )
        return (
            {row["tablename"] for row in tables},
            {row["typname"] for row in enums},
            {row["proname"] for row in functions},
        )
    finally:
        await connection.close()


def test_migrations_upgrade_and_downgrade(database_urls) -> None:
    owner_url = database_urls["owner"]
    asyncio.run(_create_database(owner_url))

    migration_url = make_url(owner_url).set(database=MIGRATION_DB_NAME)
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option(
        "sqlalchemy.url",
        migration_url.render_as_string(hide_password=False),
    )

    expected_tables = {
        "tenants",
        "users",
        "services",
        "packages",
        "package_items",
        "subscription_plans",
        "subscription_plan_items",
        "clients",
        "client_score_events",
        "lgpd_consents",
        "medical_records",
        "medical_record_attachments",
        "audit_logs",
    }
    expected_enums = {
        "user_role",
        "tax_regime",
        "commission_base",
        "billing_cycle",
        "client_score_rating",
    }

    try:
        command.upgrade(config, "head")
        tables, enums, functions = asyncio.run(_schema(owner_url))
        assert expected_tables <= tables
        assert expected_enums <= enums
        assert "resolve_tenant_id_by_slug" in functions

        command.downgrade(config, "base")
        tables, enums, functions = asyncio.run(_schema(owner_url))
        assert expected_tables.isdisjoint(tables)
        assert expected_enums.isdisjoint(enums)
        assert "resolve_tenant_id_by_slug" not in functions

        command.upgrade(config, "head")
        tables, _, functions = asyncio.run(_schema(owner_url))
        assert expected_tables <= tables
        assert "resolve_tenant_id_by_slug" in functions
    finally:
        asyncio.run(_drop_database(owner_url))
