"""Cria agendamentos com constraint anti-overlap e RLS.

Revision ID: 0007_appointments
Revises: 0006_clients
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0007_appointments"
down_revision: str | None = "0006_clients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        "CREATE TYPE appointment_status AS ENUM ("
        "'SCHEDULED', 'PENDING_DEPOSIT', 'CONFIRMED', "
        "'CANCELLED', 'EXPIRED', 'COMPLETED', 'NO_SHOW')"
    )

    op.create_table(
        "appointments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collaborator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "SCHEDULED",
                "PENDING_DEPOSIT",
                "CONFIRMED",
                "CANCELLED",
                "EXPIRED",
                "COMPLETED",
                "NO_SHOW",
                name="appointment_status",
                create_type=False,
            ),
            server_default=sa.text("'SCHEDULED'"),
            nullable=False,
        ),
        sa.Column(
            "deposit_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "ends_at > starts_at",
            name="ck_appointments_time_range",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_appointments_client_id_clients",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["users.id"],
            name="fk_appointments_collaborator_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_appointments_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_appointments_service_id_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_appointments_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
    )
    op.create_index("ix_appointments_tenant_id", "appointments", ["tenant_id"])
    op.create_index(
        "ix_appointments_collaborator_id",
        "appointments",
        ["collaborator_id"],
    )
    op.create_index("ix_appointments_client_id", "appointments", ["client_id"])
    op.create_index("ix_appointments_service_id", "appointments", ["service_id"])
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])

    # Nível 2 da trava anti-double-booking: o banco impede matematicamente
    # intervalos sobrepostos para o mesmo profissional, mesmo sob concorrência.
    op.execute(
        "ALTER TABLE appointments ADD CONSTRAINT ex_appointments_no_overlap "
        "EXCLUDE USING gist ("
        "tenant_id WITH =, collaborator_id WITH =, "
        "tstzrange(starts_at, ends_at, '[)') WITH &&"
        ") WHERE (status NOT IN ('CANCELLED', 'EXPIRED'))"
    )

    op.execute("ALTER TABLE appointments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE appointments FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY appointments_tenant_isolation ON appointments "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("appointments")
    op.execute("DROP TYPE IF EXISTS appointment_status")
