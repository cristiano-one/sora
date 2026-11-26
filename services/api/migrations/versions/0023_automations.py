"""Motor de automações e execuções agendadas.

Revision ID: 0023_automations
Revises: 0022_appointment_checkin
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_automations"
down_revision: str | None = "0022_appointment_checkin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE automation_trigger AS ENUM ("
        "'BOOKING_CONFIRMATION', 'REMINDER_24H', 'REMINDER_2H', "
        "'POST_SERVICE', 'WINBACK_60D', 'BIRTHDAY')"
    )
    op.execute(
        "CREATE TYPE automation_run_status AS ENUM ("
        "'PENDING', 'SENT', 'SKIPPED', 'FAILED')"
    )

    op.create_table(
        "automation_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "trigger",
            postgresql.ENUM(
                "BOOKING_CONFIRMATION",
                "REMINDER_24H",
                "REMINDER_2H",
                "POST_SERVICE",
                "WINBACK_60D",
                "BIRTHDAY",
                name="automation_trigger",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column(
            "delay_minutes",
            sa.Integer(),
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
            "delay_minutes >= -10080 AND delay_minutes <= 10080",
            name="ck_automation_rules_delay",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_automation_rules_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_automation_rules"),
        sa.UniqueConstraint(
            "tenant_id",
            "trigger",
            name="uq_automation_rules_tenant_id_trigger",
        ),
    )
    op.create_index(
        "ix_automation_rules_tenant_id",
        "automation_rules",
        ["tenant_id"],
    )

    op.create_table(
        "automation_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "SENT",
                "SKIPPED",
                "FAILED",
                name="automation_run_status",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_automation_runs_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_automation_runs_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["automation_rules.id"],
            name="fk_automation_runs_rule_id_automation_rules",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_automation_runs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_automation_runs"),
        sa.UniqueConstraint(
            "tenant_id",
            "dedupe_key",
            name="uq_automation_runs_tenant_id_dedupe_key",
        ),
    )
    for column in (
        "tenant_id",
        "rule_id",
        "client_id",
        "appointment_id",
        "status",
        "scheduled_for",
    ):
        op.create_index(
            f"ix_automation_runs_{column}",
            "automation_runs",
            [column],
        )

    for table in ("automation_rules", "automation_runs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("automation_runs")
    op.drop_table("automation_rules")
    op.execute("DROP TYPE automation_run_status")
    op.execute("DROP TYPE automation_trigger")
