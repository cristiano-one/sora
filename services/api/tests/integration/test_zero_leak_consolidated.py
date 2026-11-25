"""Suíte consolidada Zero-Leak: RLS em todas as tabelas do tenant."""

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.security, pytest.mark.integration]

RLS_TABLES = {
    "tenants",
    "tenant_settings",
    "users",
    "services",
    "packages",
    "package_items",
    "subscription_plans",
    "subscription_plan_items",
    "client_subscriptions",
    "subscription_usages",
    "clients",
    "client_score_events",
    "lgpd_consents",
    "medical_records",
    "medical_record_attachments",
    "audit_logs",
    "appointments",
    "payment_intents",
}


async def test_all_tables_enforce_row_level_security(app_session) -> None:
    result = await app_session.execute(
        text(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        )
    )
    flags = {
        row.relname: (row.relrowsecurity, row.relforcerowsecurity)
        for row in result
    }

    missing = RLS_TABLES - set(flags)
    unexpected = set(flags) - RLS_TABLES - {"alembic_version"}

    assert not missing, f"Tabelas sem RLS: {sorted(missing)}"
    assert not unexpected, f"Tabelas novas sem RLS: {sorted(unexpected)}"
    assert all(flags[table] == (True, True) for table in RLS_TABLES)


async def test_all_tables_have_tenant_isolation_policy(app_session) -> None:
    result = await app_session.execute(
        text(
            "SELECT tablename, policyname FROM pg_policies "
            "WHERE schemaname = 'public'"
        )
    )
    policies = {
        row.tablename: row.policyname
        for row in result
        if "tenant_isolation" in row.policyname
    }

    missing = RLS_TABLES - set(policies)
    assert not missing, f"Tabelas sem policy de isolamento: {sorted(missing)}"


async def test_runtime_role_has_no_rls_bypass(app_session) -> None:
    result = await app_session.execute(
        text(
            "SELECT rolsuper, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        )
    )
    row = result.one()

    assert row.rolsuper is False
    assert row.rolbypassrls is False
