"""graph read model

Revision ID: 202606260004
Revises: 202606260003
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202606260004"
down_revision = "202606260003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_nodes",
        sa.Column("node_id", sa.String(length=256), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(length=256), nullable=True),
        sa.Column("label", sa.String(length=1024), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_graph_nodes")),
    )
    op.create_index(op.f("ix_graph_nodes_node_type"), "graph_nodes", ["node_type"])
    op.create_index(op.f("ix_graph_nodes_entity_id"), "graph_nodes", ["entity_id"])
    op.create_index(op.f("ix_graph_nodes_external_id"), "graph_nodes", ["external_id"])
    op.create_table(
        "graph_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node_id", sa.String(length=256), nullable=False),
        sa.Column("target_node_id", sa.String(length=256), nullable=False),
        sa.Column("edge_type", sa.String(length=128), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_graph_edges")),
        sa.UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "edge_type",
            name="uq_graph_edges_source_target_type",
        ),
    )
    op.create_index(op.f("ix_graph_edges_source_node_id"), "graph_edges", ["source_node_id"])
    op.create_index(op.f("ix_graph_edges_target_node_id"), "graph_edges", ["target_node_id"])
    op.create_index(op.f("ix_graph_edges_edge_type"), "graph_edges", ["edge_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_graph_edges_edge_type"), table_name="graph_edges")
    op.drop_index(op.f("ix_graph_edges_target_node_id"), table_name="graph_edges")
    op.drop_index(op.f("ix_graph_edges_source_node_id"), table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index(op.f("ix_graph_nodes_external_id"), table_name="graph_nodes")
    op.drop_index(op.f("ix_graph_nodes_entity_id"), table_name="graph_nodes")
    op.drop_index(op.f("ix_graph_nodes_node_type"), table_name="graph_nodes")
    op.drop_table("graph_nodes")
