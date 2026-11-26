"""Persona da SORA IA e aprovação humana de exceções.

Revision ID: 0016_ai_persona_approval
Revises: 0015_inventory
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_ai_persona_approval"
down_revision: str | None = "0015_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_settings",
        sa.Column(
            "agent_tone",
            sa.String(length=30),
            server_default=sa.text("'acolhedor'"),
            nullable=False,
        ),
    )
    for column in (
        "agent_welcome_message",
        "agent_knowledge",
        "agent_cancellation_policy",
        "agent_address_info",
        "agent_upsell",
    ):
        op.add_column(
            "tenant_settings",
            sa.Column(column, sa.Text(), nullable=True),
        )

    op.add_column(
        "ai_conversations",
        sa.Column(
            "needs_approval",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_conversations",
        sa.Column("approval_note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_ai_conversations_needs_approval",
        "ai_conversations",
        ["needs_approval"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_conversations_needs_approval",
        table_name="ai_conversations",
    )
    op.drop_column("ai_conversations", "approval_note")
    op.drop_column("ai_conversations", "needs_approval")
    for column in (
        "agent_upsell",
        "agent_address_info",
        "agent_cancellation_policy",
        "agent_knowledge",
        "agent_welcome_message",
        "agent_tone",
    ):
        op.drop_column("tenant_settings", column)
