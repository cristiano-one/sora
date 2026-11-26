"""Folha de pagamento, adiantamentos e pró-labore.

Revision ID: 0017_payroll
Revises: 0016_ai_persona_approval
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_payroll"
down_revision: str | None = "0016_ai_persona_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
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
        sa.Column("cash_date", sa.Date(), nullable=True),
        sa.Column(
            "financial_entry_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
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
        sa.CheckConstraint("amount > 0", name="ck_payroll_entries_amount"),
        sa.CheckConstraint(
            "status != 'PAID' OR cash_date IS NOT NULL",
            name="ck_payroll_entries_paid_cash_date",
        ),
        sa.CheckConstraint(
            "kind IN ('SALARY', 'ADVANCE', 'PRO_LABORE', 'COMMISSION_PAYOUT')",
            name="ck_payroll_entries_kind",
        ),
        sa.ForeignKeyConstraint(
            ["financial_entry_id"],
            ["financial_entries.id"],
            name="fk_payroll_entries_financial_entry_id_financial_entries",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_payroll_entries_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_payroll_entries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payroll_entries"),
    )
    op.create_index(
        "ix_payroll_entries_tenant_id",
        "payroll_entries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_payroll_entries_user_id",
        "payroll_entries",
        ["user_id"],
    )
    op.create_index(
        "ix_payroll_entries_status",
        "payroll_entries",
        ["status"],
    )

    op.execute("ALTER TABLE payroll_entries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payroll_entries FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY payroll_entries_tenant_isolation ON payroll_entries "
        "USING (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("payroll_entries")
