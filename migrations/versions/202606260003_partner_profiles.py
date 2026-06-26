"""partner profiles

Revision ID: 202606260003
Revises: 202606260002
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202606260003"
down_revision = "202606260002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("layout_signature", sa.String(length=256), nullable=False),
        sa.Column("sheet_name", sa.String(length=256), nullable=True),
        sa.Column("header_row_index", sa.Integer(), nullable=True),
        sa.Column("service_column", sa.String(length=32), nullable=True),
        sa.Column("service_code_column", sa.String(length=32), nullable=True),
        sa.Column("resident_price_column", sa.String(length=32), nullable=True),
        sa.Column("nonresident_price_column", sa.String(length=32), nullable=True),
        sa.Column("normalization_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("learned_from_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], name=op.f("fk_partner_profiles_partner_id_partners")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partner_profiles")),
        sa.UniqueConstraint("partner_id", name=op.f("uq_partner_profiles_partner_id")),
    )
    op.create_index(op.f("ix_partner_profiles_partner_id"), "partner_profiles", ["partner_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_partner_profiles_partner_id"), table_name="partner_profiles")
    op.drop_table("partner_profiles")
