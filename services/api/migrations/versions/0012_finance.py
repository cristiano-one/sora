"""Cria contas/lançamentos financeiros e dízimo/oferta.

Revision ID: 0012_finance
Revises: 0011_payment_intents
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0012_finance"
down_revision: str | None = "0011_payment_intents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE account_type AS ENUM ('CASH', 'BANK')")
    op.execute(
        "CREATE TYPE financial_entry_type AS ENUM ('INCOME', 'EXPENSE')"
    )
    op.execute(
        "CREATE TYPE financial_entry_status AS ENUM ('PENDING', 'PAID')"
    )
    op.execute(
        "CREATE TYPE financial_category AS ENUM ("
        "'SERVICE', 'PACKAGE', 'SUBSCRIPTION', 'PRODUCT', 'OTHER_INCOME', "
        "'TAX', 'CARD_FEE', 'SUPPLIES', 'COMMISSION', 'RENT', 'UTILITY', "
        "'MARKETING', 'PAYROLL', 'OTHER_EXPENSE')"
    )

    op.create_table(
        "financial_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "CASH",
                "BANK",
                name="account_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "initial_balance",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
            "initial_balance >= 0",
            name="ck_financial_accounts_initial_balance",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_financial_accounts_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_accounts"),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_financial_accounts_tenant_id_name",
        ),
    )
    op.create_index(
        "ix_financial_accounts_tenant_id",
        "financial_accounts",
        ["tenant_id"],
    )

    op.create_table(
        "financial_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "INCOME",
                "EXPENSE",
                name="financial_entry_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "category",
            postgresql.ENUM(
                "SERVICE",
                "PACKAGE",
                "SUBSCRIPTION",
                "PRODUCT",
                "OTHER_INCOME",
                "TAX",
                "CARD_FEE",
                "SUPPLIES",
                "COMMISSION",
                "RENT",
                "UTILITY",
                "MARKETING",
                "PAYROLL",
                "OTHER_EXPENSE",
                name="financial_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("cash_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "PAID",
                name="financial_entry_status",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            "amount > 0",
            name="ck_financial_entries_amount",
        ),
        sa.CheckConstraint(
            "status <> 'PAID' OR cash_date IS NOT NULL",
            name="ck_financial_entries_paid_cash_date",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["financial_accounts.id"],
            name="fk_financial_entries_account_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_financial_entries_appointment_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_financial_entries_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_financial_entries_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_entries"),
    )
    op.create_index(
        "ix_financial_entries_tenant_id",
        "financial_entries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_financial_entries_account_id",
        "financial_entries",
        ["account_id"],
    )
    op.create_index(
        "ix_financial_entries_category",
        "financial_entries",
        ["category"],
    )
    op.create_index(
        "ix_financial_entries_competence_date",
        "financial_entries",
        ["competence_date"],
    )
    op.create_index(
        "ix_financial_entries_cash_date",
        "financial_entries",
        ["cash_date"],
    )
    op.create_index(
        "ix_financial_entries_status",
        "financial_entries",
        ["status"],
    )
    op.create_index(
        "ix_financial_entries_appointment_id",
        "financial_entries",
        ["appointment_id"],
    )

    op.add_column(
        "tenant_settings",
        sa.Column(
            "enable_tithe_and_offering",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "tithe_percentage",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("10"),
            nullable=False,
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "offering_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_tenant_settings_tithe_percentage",
        "tenant_settings",
        "tithe_percentage >= 0 AND tithe_percentage <= 100",
    )
    op.create_check_constraint(
        "ck_tenant_settings_offering_amount",
        "tenant_settings",
        "offering_amount >= 0",
    )

    for table in ("financial_accounts", "financial_entries"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("financial_entries")
    op.drop_table("financial_accounts")
    op.drop_constraint(
        "ck_tenant_settings_offering_amount",
        "tenant_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_tenant_settings_tithe_percentage",
        "tenant_settings",
        type_="check",
    )
    op.drop_column("tenant_settings", "offering_amount")
    op.drop_column("tenant_settings", "tithe_percentage")
    op.drop_column("tenant_settings", "enable_tithe_and_offering")
    op.execute("DROP TYPE IF EXISTS financial_category")
    op.execute("DROP TYPE IF EXISTS financial_entry_status")
    op.execute("DROP TYPE IF EXISTS financial_entry_type")
    op.execute("DROP TYPE IF EXISTS account_type")
