"""Check-in digital e token público do agendamento.

Revision ID: 0022_appointment_checkin
Revises: 0021_sales
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_appointment_checkin"
down_revision: str | None = "0021_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("checkin_token", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE appointments SET checkin_token = "
        "replace(gen_random_uuid()::text, '-', '') "
        "WHERE checkin_token IS NULL"
    )
    op.alter_column(
        "appointments",
        "checkin_token",
        nullable=False,
        server_default=sa.text("replace(gen_random_uuid()::text, '-', '')"),
    )
    op.create_unique_constraint(
        "uq_appointments_checkin_token",
        "appointments",
        ["checkin_token"],
    )
    op.create_index(
        "ix_appointments_checkin_token",
        "appointments",
        ["checkin_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointments_checkin_token",
        table_name="appointments",
    )
    op.drop_constraint(
        "uq_appointments_checkin_token",
        "appointments",
        type_="unique",
    )
    op.drop_column("appointments", "checked_in_at")
    op.drop_column("appointments", "checkin_token")
