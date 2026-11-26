"""Vínculo parceiro/MEI e NFS-e.

Revision ID: 0024_fiscal_partner
Revises: 0023_automations
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_fiscal_partner"
down_revision: str | None = "0023_automations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE employment_type AS ENUM ('EMPLOYEE', 'PARTNER', 'MEI')")
    op.add_column(
        "users",
        sa.Column(
            "employment_type",
            postgresql.ENUM(
                "EMPLOYEE",
                "PARTNER",
                "MEI",
                name="employment_type",
                create_type=False,
            ),
            server_default=sa.text("'EMPLOYEE'"),
            nullable=False,
        ),
    )

    for column, kind in (
        ("fiscal_municipality", sa.String(length=120)),
        ("fiscal_service_code", sa.String(length=60)),
        ("fiscal_email", sa.String(length=255)),
    ):
        op.add_column(
            "tenant_settings",
            sa.Column(column, kind, nullable=True),
        )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "fiscal_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "fiscal_provider",
            sa.String(length=30),
            server_default=sa.text("'mock'"),
            nullable=False,
        ),
    )

    op.execute(
        "CREATE TYPE fiscal_invoice_status AS ENUM ('ISSUED', 'CANCELLED', 'ERROR')"
    )
    op.create_table(
        "fiscal_invoices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ISSUED",
                "CANCELLED",
                "ERROR",
                name="fiscal_invoice_status",
                create_type=False,
            ),
            server_default=sa.text("'ISSUED'"),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=30),
            server_default=sa.text("'mock'"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint("amount >= 0", name="ck_fiscal_invoices_amount"),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_fiscal_invoices_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_fiscal_invoices_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fiscal_invoices"),
        sa.UniqueConstraint(
            "tenant_id",
            "sale_id",
            name="uq_fiscal_invoices_tenant_id_sale_id",
        ),
    )
    op.create_index(
        "ix_fiscal_invoices_tenant_id",
        "fiscal_invoices",
        ["tenant_id"],
    )
    op.create_index(
        "ix_fiscal_invoices_sale_id",
        "fiscal_invoices",
        ["sale_id"],
    )
    op.execute("ALTER TABLE fiscal_invoices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fiscal_invoices FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY fiscal_invoices_tenant_isolation ON fiscal_invoices "
        "USING (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("fiscal_invoices")
    op.execute("DROP TYPE fiscal_invoice_status")
    for column in (
        "fiscal_provider",
        "fiscal_enabled",
        "fiscal_email",
        "fiscal_service_code",
        "fiscal_municipality",
    ):
        op.drop_column("tenant_settings", column)
    op.drop_column("users", "employment_type")
    op.execute("DROP TYPE employment_type")
