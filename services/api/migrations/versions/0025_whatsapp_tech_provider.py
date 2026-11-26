"""Conta WhatsApp Business (Tech Provider) por tenant e idempotência de mensagens.

Revision ID: 0025_whatsapp_tech_provider
Revises: 0024_fiscal_partner
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_whatsapp_tech_provider"
down_revision: str | None = "0024_fiscal_partner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE whatsapp_connection_status AS ENUM "
        "('CONNECTED', 'DISCONNECTED', 'ERROR')"
    )
    op.create_table(
        "tenant_whatsapp_accounts",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "CONNECTED",
                "DISCONNECTED",
                "ERROR",
                name="whatsapp_connection_status",
                create_type=False,
            ),
            server_default=sa.text("'DISCONNECTED'"),
            nullable=False,
        ),
        sa.Column("waba_id", sa.String(length=64), nullable=True),
        sa.Column("phone_number_id", sa.String(length=64), nullable=True),
        sa.Column("display_phone_number", sa.String(length=32), nullable=True),
        sa.Column("verified_name", sa.String(length=255), nullable=True),
        sa.Column("quality_rating", sa.String(length=30), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "registration_status",
            sa.String(length=20),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("registration_error", sa.String(length=500), nullable=True),
        sa.Column("registration_pin_encrypted", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status <> 'CONNECTED' OR "
            "(waba_id IS NOT NULL AND phone_number_id IS NOT NULL "
            "AND access_token_encrypted IS NOT NULL)",
            name="ck_tenant_whatsapp_connected_fields",
        ),
        sa.CheckConstraint(
            "registration_status IN "
            "('PENDING', 'REGISTERED', 'FAILED', 'SKIPPED')",
            name="ck_tenant_whatsapp_registration_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tenant_whatsapp_accounts_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["connected_by"],
            ["users.id"],
            name="fk_tenant_whatsapp_accounts_connected_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("tenant_id", name="pk_tenant_whatsapp_accounts"),
        sa.UniqueConstraint(
            "phone_number_id",
            name="uq_tenant_whatsapp_accounts_phone_number_id",
        ),
    )

    op.execute("ALTER TABLE tenant_whatsapp_accounts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_whatsapp_accounts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_whatsapp_accounts_tenant_isolation "
        "ON tenant_whatsapp_accounts "
        "USING (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )

    # O webhook da Meta chega sem JWT/tenant; esta função expõe somente o
    # tenant_id necessário para rotear a mensagem, nunca token ou dados.
    op.execute(
        """
        CREATE FUNCTION public.resolve_tenant_id_by_whatsapp_phone(
            p_phone_number_id text
        )
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT tenant_id
            FROM public.tenant_whatsapp_accounts
            WHERE phone_number_id = p_phone_number_id
              AND status = 'CONNECTED'
            LIMIT 1
        $$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "public.resolve_tenant_id_by_whatsapp_phone(text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION "
        "public.resolve_tenant_id_by_whatsapp_phone(text) TO sora_app"
    )

    # Idempotência: a Meta pode reenviar o mesmo webhook.
    op.add_column(
        "ai_messages",
        sa.Column("external_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_ai_messages_tenant_external_id",
        "ai_messages",
        ["tenant_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_messages_tenant_external_id", table_name="ai_messages")
    op.drop_column("ai_messages", "external_id")
    op.execute(
        "DROP FUNCTION IF EXISTS "
        "public.resolve_tenant_id_by_whatsapp_phone(text)"
    )
    op.drop_table("tenant_whatsapp_accounts")
    op.execute("DROP TYPE whatsapp_connection_status")
