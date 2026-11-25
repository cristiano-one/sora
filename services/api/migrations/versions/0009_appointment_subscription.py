"""Vincula agendamentos a assinaturas (consumo de cota).

Revision ID: 0009_appointment_subscription
Revises: 0008_subscriptions
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0009_appointment_subscription"
down_revision: str | None = "0008_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_appointments_subscription_id_client_subscriptions",
        "appointments",
        "client_subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_appointments_subscription_id",
        "appointments",
        ["subscription_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_subscription_id", table_name="appointments")
    op.drop_constraint(
        "fk_appointments_subscription_id_client_subscriptions",
        "appointments",
        type_="foreignkey",
    )
    op.drop_column("appointments", "subscription_id")
