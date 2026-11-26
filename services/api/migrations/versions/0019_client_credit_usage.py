"""Histórico de utilização de créditos de clientes.

Revision ID: 0019_client_credit_usage
Revises: 0018_tithe_delivery
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_client_credit_usage"
down_revision: str | None = "0018_tithe_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_credit_usages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_client_credit_usages_amount",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_client_credit_usages_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_client_credit_usages_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_client_credit_usages_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["credit_id"],
            ["client_credits.id"],
            name="fk_client_credit_usages_credit_id_client_credits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_client_credit_usages_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_client_credit_usages"),
    )
    op.create_index(
        "ix_client_credit_usages_tenant_id",
        "client_credit_usages",
        ["tenant_id"],
    )
    op.create_index(
        "ix_client_credit_usages_credit_id",
        "client_credit_usages",
        ["credit_id"],
    )
    op.create_index(
        "ix_client_credit_usages_client_id",
        "client_credit_usages",
        ["client_id"],
    )
    op.create_index(
        "ix_client_credit_usages_appointment_id",
        "client_credit_usages",
        ["appointment_id"],
    )
    op.execute("ALTER TABLE client_credit_usages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_credit_usages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_credit_usages_tenant_isolation "
        "ON client_credit_usages "
        "USING (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("client_credit_usages")
