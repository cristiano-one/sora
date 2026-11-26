"""Perfil de negócio por tenant.

Revision ID: 0020_business_profile
Revises: 0019_client_credit_usage
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_business_profile"
down_revision: str | None = "0019_client_credit_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE business_profile AS ENUM ("
        "'MEDICAL_CLINIC', 'AESTHETICS', 'PODOLOGY', 'SALON', "
        "'BARBERSHOP', 'GENERAL')"
    )
    op.add_column(
        "tenants",
        sa.Column(
            "business_profile",
            sa.Enum(
                "MEDICAL_CLINIC",
                "AESTHETICS",
                "PODOLOGY",
                "SALON",
                "BARBERSHOP",
                "GENERAL",
                name="business_profile",
                create_type=False,
            ),
            server_default=sa.text("'AESTHETICS'"),
            nullable=False,
        ),
    )
    # Tenants novos nascem como GENERAL até o administrador do sistema
    # definir o segmento no console master.
    op.alter_column(
        "tenants",
        "business_profile",
        server_default=sa.text("'GENERAL'"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "business_profile")
    op.execute("DROP TYPE business_profile")
