"""Testes Zero-Leak de isolamento multi-tenant garantido pela RLS."""

import pytest
from app.db.rls import set_tenant_context
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.security, pytest.mark.integration]


async def _user_ids(session: AsyncSession) -> list[str]:
    result = await session.execute(text("SELECT id FROM users"))
    return [str(user_id) for user_id in result.scalars().all()]


async def test_select_returns_only_current_tenant(app_session, seeded) -> None:
    await set_tenant_context(app_session, seeded.tenant_a)

    assert await _user_ids(app_session) == [str(seeded.user_a)]
    await app_session.rollback()


async def test_cannot_read_other_tenant_by_explicit_id(app_session, seeded) -> None:
    await set_tenant_context(app_session, seeded.tenant_a)

    result = await app_session.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": seeded.user_b},
    )

    assert result.scalars().all() == []
    await app_session.rollback()


async def test_cannot_insert_into_other_tenant(app_session, seeded) -> None:
    await set_tenant_context(app_session, seeded.tenant_a)

    with pytest.raises(DBAPIError):
        await app_session.execute(
            text(
                "INSERT INTO users (tenant_id, email, hashed_password, full_name, role) "
                "VALUES (:tenant_id, :email, :hashed_password, :full_name, 'OWNER')"
            ),
            {
                "tenant_id": seeded.tenant_b,
                "email": "intruso@test.local",
                "hashed_password": "x",
                "full_name": "Intruso",
            },
        )

    await app_session.rollback()


async def test_update_and_delete_do_not_touch_other_tenant(app_session, seeded) -> None:
    await set_tenant_context(app_session, seeded.tenant_a)

    updated = await app_session.execute(
        text("UPDATE users SET full_name = 'x' WHERE id = :user_id"),
        {"user_id": seeded.user_b},
    )
    deleted = await app_session.execute(
        text("DELETE FROM users WHERE id = :user_id"),
        {"user_id": seeded.user_b},
    )

    assert updated.rowcount == 0
    assert deleted.rowcount == 0
    await app_session.rollback()


async def test_without_context_returns_no_rows(app_session, seeded) -> None:
    assert await _user_ids(app_session) == []
    await app_session.rollback()


async def test_invalid_context_fails_closed(app_session, seeded) -> None:
    await app_session.execute(
        text("SELECT set_config('app.current_tenant_id', 'not-a-uuid', true)")
    )

    with pytest.raises(DBAPIError):
        await _user_ids(app_session)

    await app_session.rollback()


async def test_tenants_table_also_isolated(app_session, seeded) -> None:
    await set_tenant_context(app_session, seeded.tenant_a)

    result = await app_session.execute(text("SELECT id FROM tenants"))

    assert [str(tenant_id) for tenant_id in result.scalars().all()] == [
        str(seeded.tenant_a)
    ]
    await app_session.rollback()


async def test_runtime_role_has_no_rls_bypass(app_session) -> None:
    result = await app_session.execute(
        text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )
    row = result.one()

    assert row.rolsuper is False
    assert row.rolbypassrls is False


async def test_tables_enforce_rls(app_session) -> None:
    result = await app_session.execute(
        text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname IN ('tenants', 'users') ORDER BY relname"
        )
    )

    assert [tuple(row) for row in result.all()] == [
        ("tenants", True, True),
        ("users", True, True),
    ]
