"""Adiciona regras de comissão aos usuários.

Revision ID: 0004_user_commissions
Revises: 0003_tenant_tax_regime
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0004_user_commissions"
down_revision: str | None = "0003_tenant_tax_regime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE commission_base AS ENUM ('GROSS', 'NET')")
    op.add_column(
        "users",
        sa.Column(
            "commission_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "commission_fixed",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "commission_base",
            postgresql.ENUM(
                "GROSS",
                "NET",
                name="commission_base",
                create_type=False,
            ),
            server_default=sa.text("'GROSS'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "commission_base")
    op.drop_column("users", "commission_fixed")
    op.drop_column("users", "commission_percentage")
    op.execute("DROP TYPE IF EXISTS commission_base")
