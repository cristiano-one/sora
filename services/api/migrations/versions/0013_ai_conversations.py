"""Cria conversas/mensagens da SORA IA com RLS.

Revision ID: 0013_ai_conversations
Revises: 0012_finance
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0013_ai_conversations"
down_revision: str | None = "0012_finance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE conversation_status AS ENUM ('OPEN', 'HUMAN', 'CLOSED')"
    )
    op.execute(
        "CREATE TYPE message_direction AS ENUM ('INBOUND', 'OUTBOUND')"
    )

    op.create_table(
        "ai_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=30),
            server_default=sa.text("'WHATSAPP'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "OPEN",
                "HUMAN",
                "CLOSED",
                name="conversation_status",
                create_type=False,
            ),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_ai_conversations_client_id_clients",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_ai_conversations_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_conversations"),
    )
    op.create_index(
        "ix_ai_conversations_tenant_id",
        "ai_conversations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_ai_conversations_client_id",
        "ai_conversations",
        ["client_id"],
    )
    op.create_index(
        "ix_ai_conversations_phone",
        "ai_conversations",
        ["phone"],
    )
    op.create_index(
        "ix_ai_conversations_status",
        "ai_conversations",
        ["status"],
    )
    op.create_index(
        "ix_ai_conversations_last_message_at",
        "ai_conversations",
        ["last_message_at"],
    )

    op.create_table(
        "ai_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "direction",
            postgresql.ENUM(
                "INBOUND",
                "OUTBOUND",
                name="message_direction",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            name="fk_ai_messages_conversation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_ai_messages_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_messages"),
    )
    op.create_index("ix_ai_messages_tenant_id", "ai_messages", ["tenant_id"])
    op.create_index(
        "ix_ai_messages_conversation_id",
        "ai_messages",
        ["conversation_id"],
    )

    for table in ("ai_conversations", "ai_messages"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.execute("DROP TYPE IF EXISTS message_direction")
    op.execute("DROP TYPE IF EXISTS conversation_status")
