"""outbox projection state

Revision ID: 202606260005
Revises: 202606260004
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202606260005"
down_revision = "202606260004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("status", sa.String(length=64), nullable=False, server_default="pending"),
    )
    op.add_column("outbox_events", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "outbox_events",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"])
    op.create_index(op.f("ix_outbox_events_next_retry_at"), "outbox_events", ["next_retry_at"])
    op.execute(
        """
        UPDATE outbox_events
        SET status = CASE WHEN published_at IS NULL THEN 'pending' ELSE 'completed' END,
            processed_at = published_at
        """
    )
    op.alter_column("outbox_events", "status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_next_retry_at"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_status"), table_name="outbox_events")
    op.drop_column("outbox_events", "processed_at")
    op.drop_column("outbox_events", "processing_started_at")
    op.drop_column("outbox_events", "next_retry_at")
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "status")
