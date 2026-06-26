"""initial core schema

Revision ID: 202606260001
Revises:
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606260001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_partner_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("bin", sa.String(length=12), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partners")),
        sa.UniqueConstraint("external_partner_id", name=op.f("uq_partners_external_partner_id")),
    )
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_service_id", sa.String(length=128), nullable=True),
        sa.Column("official_name", sa.String(length=1024), nullable=False),
        sa.Column("category", sa.String(length=256), nullable=True),
        sa.Column("synonyms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
        sa.UniqueConstraint("external_service_id", name=op.f("uq_services_external_service_id")),
    )
    op.create_table(
        "ingestion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("documents_total", sa.Integer(), nullable=False),
        sa.Column("documents_processed", sa.Integer(), nullable=False),
        sa.Column("documents_failed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_batches")),
    )
    op.create_table(
        "source_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("detected_mime_type", sa.String(length=256), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=2048), nullable=False),
        sa.Column("malware_scan_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"], name=op.f("fk_source_files_batch_id_ingestion_batches")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_files")),
        sa.UniqueConstraint("sha256", "batch_id", name="uq_source_files_sha256_batch"),
        sa.UniqueConstraint("storage_key", name=op.f("uq_source_files_storage_key")),
    )
    op.create_index(op.f("ix_source_files_batch_id"), "source_files", ["batch_id"], unique=False)
    op.create_index(op.f("ix_source_files_sha256"), "source_files", ["sha256"], unique=False)
    op.create_table(
        "price_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_source_id", sa.String(length=256), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("detected_format", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], name=op.f("fk_price_documents_partner_id_partners")),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"], name=op.f("fk_price_documents_source_file_id_source_files")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_documents")),
    )
    op.create_index(op.f("ix_price_documents_external_source_id"), "price_documents", ["external_source_id"], unique=False)
    op.create_index(op.f("ix_price_documents_partner_id"), "price_documents", ["partner_id"], unique=False)
    op.create_index(op.f("ix_price_documents_source_file_id"), "price_documents", ["source_file_id"], unique=False)
    op.create_index(op.f("ix_price_documents_status"), "price_documents", ["status"], unique=False)
    op.create_table(
        "processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=128), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("matcher_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["price_documents.id"], name=op.f("fk_processing_runs_document_id_price_documents")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_runs")),
    )
    op.create_index(op.f("ix_processing_runs_document_id"), "processing_runs", ["document_id"], unique=False)
    op.create_table(
        "extracted_price_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(length=256), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("source_bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("service_name_raw", sa.Text(), nullable=False),
        sa.Column("service_code_raw", sa.String(length=256), nullable=True),
        sa.Column("resident_price_raw", sa.String(length=128), nullable=True),
        sa.Column("nonresident_price_raw", sa.String(length=128), nullable=True),
        sa.Column("currency_raw", sa.String(length=16), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["processing_run_id"], ["processing_runs.id"], name=op.f("fk_extracted_price_items_processing_run_id_processing_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extracted_price_items")),
    )
    op.create_index(op.f("ix_extracted_price_items_processing_run_id"), "extracted_price_items", ["processing_run_id"], unique=False)
    op.create_table(
        "service_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extracted_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_method", sa.String(length=128), nullable=False),
        sa.Column("retrieval_score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("reranker_score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("matcher_version", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["extracted_item_id"], ["extracted_price_items.id"], name=op.f("fk_service_matches_extracted_item_id_extracted_price_items")),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], name=op.f("fk_service_matches_service_id_services")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_matches")),
    )
    op.create_index(op.f("ix_service_matches_extracted_item_id"), "service_matches", ["extracted_item_id"], unique=False)
    op.create_index(op.f("ix_service_matches_service_id"), "service_matches", ["service_id"], unique=False)
    op.create_table(
        "review_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extracted_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["extracted_item_id"], ["extracted_price_items.id"], name=op.f("fk_review_tasks_extracted_item_id_extracted_price_items")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_tasks")),
    )
    op.create_index(op.f("ix_review_tasks_extracted_item_id"), "review_tasks", ["extracted_item_id"], unique=False)
    op.create_table(
        "price_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resident_price_kzt", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("nonresident_price_kzt", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("original_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("original_currency", sa.String(length=16), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(precision=14, scale=6), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(length=64), nullable=False),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], name=op.f("fk_price_versions_partner_id_partners")),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], name=op.f("fk_price_versions_service_id_services")),
        sa.ForeignKeyConstraint(["source_document_id"], ["price_documents.id"], name=op.f("fk_price_versions_source_document_id_price_documents")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_versions")),
    )
    op.create_index(op.f("ix_price_versions_partner_id"), "price_versions", ["partner_id"], unique=False)
    op.create_index(op.f("ix_price_versions_service_id"), "price_versions", ["service_id"], unique=False)
    op.create_index(op.f("ix_price_versions_source_document_id"), "price_versions", ["source_document_id"], unique=False)
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=256), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(op.f("ix_outbox_events_event_type"), "outbox_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_event_type"), table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(op.f("ix_audit_events_entity_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_price_versions_source_document_id"), table_name="price_versions")
    op.drop_index(op.f("ix_price_versions_service_id"), table_name="price_versions")
    op.drop_index(op.f("ix_price_versions_partner_id"), table_name="price_versions")
    op.drop_table("price_versions")
    op.drop_index(op.f("ix_review_tasks_extracted_item_id"), table_name="review_tasks")
    op.drop_table("review_tasks")
    op.drop_index(op.f("ix_service_matches_service_id"), table_name="service_matches")
    op.drop_index(op.f("ix_service_matches_extracted_item_id"), table_name="service_matches")
    op.drop_table("service_matches")
    op.drop_index(op.f("ix_extracted_price_items_processing_run_id"), table_name="extracted_price_items")
    op.drop_table("extracted_price_items")
    op.drop_index(op.f("ix_processing_runs_document_id"), table_name="processing_runs")
    op.drop_table("processing_runs")
    op.drop_index(op.f("ix_price_documents_status"), table_name="price_documents")
    op.drop_index(op.f("ix_price_documents_source_file_id"), table_name="price_documents")
    op.drop_index(op.f("ix_price_documents_partner_id"), table_name="price_documents")
    op.drop_index(op.f("ix_price_documents_external_source_id"), table_name="price_documents")
    op.drop_table("price_documents")
    op.drop_index(op.f("ix_source_files_sha256"), table_name="source_files")
    op.drop_index(op.f("ix_source_files_batch_id"), table_name="source_files")
    op.drop_table("source_files")
    op.drop_table("ingestion_batches")
    op.drop_table("services")
    op.drop_table("partners")
