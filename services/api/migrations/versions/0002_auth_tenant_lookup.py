"""Função SECURITY DEFINER para resolver o tenant pelo slug no login.

Revision ID: 0002_auth_tenant_lookup
Revises: 0001_tenants_users
Create Date: 2026-11-25

"""

from collections.abc import Sequence

from alembic import op

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0002_auth_tenant_lookup"
down_revision: str | None = "0001_tenants_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # O login precisa descobrir o tenant_id pelo slug antes de definir o
    # contexto RLS. A função roda como owner (SECURITY DEFINER) e devolve
    # apenas o UUID — nenhum outro dado do tenant vaza para o role de runtime.
    op.execute(
        """
        CREATE FUNCTION public.resolve_tenant_id_by_slug(p_slug text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT id
            FROM public.tenants
            WHERE slug = p_slug
              AND is_active = true
            LIMIT 1
        $$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.resolve_tenant_id_by_slug(text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.resolve_tenant_id_by_slug(text) TO sora_app"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.resolve_tenant_id_by_slug(text)")
