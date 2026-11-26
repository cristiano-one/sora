"""Entregas de dízimo e oferta.

Revision ID: 0018_tithe_delivery
Revises: 0017_payroll
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_tithe_delivery"
down_revision: str | None = "0017_payroll"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tithe_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column(
            "tithe_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "offering_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
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
            "tithe_amount >= 0 AND offering_amount >= 0",
            name="ck_tithe_deliveries_amounts",
        ),
        sa.CheckConstraint(
            "tithe_amount + offering_amount > 0",
            name="ck_tithe_deliveries_total",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_tithe_deliveries_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tithe_deliveries_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tithe_deliveries"),
    )
    op.create_index(
        "ix_tithe_deliveries_tenant_id",
        "tithe_deliveries",
        ["tenant_id"],
    )
    op.execute("ALTER TABLE tithe_deliveries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tithe_deliveries FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tithe_deliveries_tenant_isolation "
        "ON tithe_deliveries "
        "USING (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("tithe_deliveries")
