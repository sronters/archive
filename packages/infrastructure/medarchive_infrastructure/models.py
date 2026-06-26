from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from medarchive_infrastructure.database import Base


def uuid_pk() -> Mapped[PyUUID]:
    return mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PartnerModel(Base, TimestampMixin):
    __tablename__ = "partners"

    id = uuid_pk()
    external_partner_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(512))
    bin: Mapped[str | None] = mapped_column(String(12))
    city: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True)


class PartnerProfileModel(Base, TimestampMixin):
    __tablename__ = "partner_profiles"

    id = uuid_pk()
    partner_id: Mapped[PyUUID] = mapped_column(ForeignKey("partners.id"), index=True, unique=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    layout_signature: Mapped[str] = mapped_column(String(256))
    sheet_name: Mapped[str | None] = mapped_column(String(256))
    header_row_index: Mapped[int | None] = mapped_column(Integer)
    service_column: Mapped[str | None] = mapped_column(String(32))
    service_code_column: Mapped[str | None] = mapped_column(String(32))
    resident_price_column: Mapped[str | None] = mapped_column(String(32))
    nonresident_price_column: Mapped[str | None] = mapped_column(String(32))
    normalization_rules: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    learned_from_document_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))
    approved_by: Mapped[PyUUID] = mapped_column(PgUUID(as_uuid=True))


class ServiceModel(Base, TimestampMixin):
    __tablename__ = "services"

    id = uuid_pk()
    external_service_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    official_name: Mapped[str] = mapped_column(String(1024))
    category: Mapped[str | None] = mapped_column(String(256))
    synonyms: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(default=True)


class IngestionBatchModel(Base, TimestampMixin):
    __tablename__ = "ingestion_batches"

    id = uuid_pk()
    source: Mapped[str] = mapped_column(String(128))
    uploaded_by: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(64), default="created")
    documents_total: Mapped[int] = mapped_column(Integer, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    documents_failed: Mapped[int] = mapped_column(Integer, default=0)


class SourceFileModel(Base, TimestampMixin):
    __tablename__ = "source_files"
    __table_args__ = (UniqueConstraint("sha256", "batch_id", name="uq_source_files_sha256_batch"),)

    id = uuid_pk()
    batch_id: Mapped[PyUUID] = mapped_column(ForeignKey("ingestion_batches.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(1024))
    detected_mime_type: Mapped[str] = mapped_column(String(256))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(2048), unique=True)
    malware_scan_status: Mapped[str] = mapped_column(String(32), default="pending")


class PriceDocumentModel(Base, TimestampMixin):
    __tablename__ = "price_documents"

    id = uuid_pk()
    source_file_id: Mapped[PyUUID] = mapped_column(ForeignKey("source_files.id"), index=True)
    partner_id: Mapped[PyUUID | None] = mapped_column(ForeignKey("partners.id"), index=True)
    external_source_id: Mapped[str | None] = mapped_column(String(256), index=True)
    effective_date: Mapped[date | None] = mapped_column(Date)
    detected_format: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="UPLOADED", index=True)


class ProcessingRunModel(Base, TimestampMixin):
    __tablename__ = "processing_runs"

    id = uuid_pk()
    document_id: Mapped[PyUUID] = mapped_column(ForeignKey("price_documents.id"), index=True)
    pipeline_version: Mapped[str] = mapped_column(String(64))
    parser_name: Mapped[str] = mapped_column(String(128))
    parser_version: Mapped[str] = mapped_column(String(64))
    matcher_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="started")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_details: Mapped[str | None] = mapped_column(Text)


class ExtractedPriceItemModel(Base, TimestampMixin):
    __tablename__ = "extracted_price_items"

    id = uuid_pk()
    processing_run_id: Mapped[PyUUID] = mapped_column(ForeignKey("processing_runs.id"), index=True)
    page_number: Mapped[int | None] = mapped_column(Integer)
    sheet_name: Mapped[str | None] = mapped_column(String(256))
    row_number: Mapped[int | None] = mapped_column(Integer)
    source_bbox: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    service_name_raw: Mapped[str] = mapped_column(Text)
    service_code_raw: Mapped[str | None] = mapped_column(String(256))
    resident_price_raw: Mapped[str | None] = mapped_column(String(128))
    nonresident_price_raw: Mapped[str | None] = mapped_column(String(128))
    currency_raw: Mapped[str | None] = mapped_column(String(16))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ServiceMatchModel(Base, TimestampMixin):
    __tablename__ = "service_matches"

    id = uuid_pk()
    extracted_item_id: Mapped[PyUUID] = mapped_column(
        ForeignKey("extracted_price_items.id"),
        index=True,
    )
    service_id: Mapped[PyUUID] = mapped_column(ForeignKey("services.id"), index=True)
    retrieval_method: Mapped[str] = mapped_column(String(128))
    retrieval_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    reranker_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    matcher_version: Mapped[str] = mapped_column(String(64))
    rank: Mapped[int] = mapped_column(Integer)


class ReviewTaskModel(Base, TimestampMixin):
    __tablename__ = "review_tasks"

    id = uuid_pk()
    extracted_item_id: Mapped[PyUUID] = mapped_column(
        ForeignKey("extracted_price_items.id"),
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(256))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), default="open")
    assigned_to: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))
    version: Mapped[int] = mapped_column(Integer, default=0)


class PriceVersionModel(Base, TimestampMixin):
    __tablename__ = "price_versions"

    id = uuid_pk()
    partner_id: Mapped[PyUUID] = mapped_column(ForeignKey("partners.id"), index=True)
    service_id: Mapped[PyUUID] = mapped_column(ForeignKey("services.id"), index=True)
    source_document_id: Mapped[PyUUID] = mapped_column(ForeignKey("price_documents.id"), index=True)
    resident_price_kzt: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    nonresident_price_kzt: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    original_currency: Mapped[str | None] = mapped_column(String(16))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(64), default="draft")
    superseded_by: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = uuid_pk()
    actor_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))
    actor_type: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(128))
    entity_id: Mapped[PyUUID] = mapped_column(PgUUID(as_uuid=True), index=True)
    before_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    after_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(256), index=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookDeliveryModel(Base):
    __tablename__ = "webhook_deliveries"

    id = uuid_pk()
    event_id: Mapped[PyUUID] = mapped_column(PgUUID(as_uuid=True), index=True)
    event_type: Mapped[str] = mapped_column(String(256), index=True)
    event_version: Mapped[int] = mapped_column(Integer)
    endpoint_url: Mapped[str] = mapped_column(String(2048))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    signature: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(64), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GraphNodeModel(Base, TimestampMixin):
    __tablename__ = "graph_nodes"

    node_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True), index=True)
    external_id: Mapped[str | None] = mapped_column(String(256), index=True)
    label: Mapped[str] = mapped_column(String(1024))
    properties: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class GraphEdgeModel(Base, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "edge_type",
            name="uq_graph_edges_source_target_type",
        ),
    )

    id = uuid_pk()
    source_node_id: Mapped[str] = mapped_column(String(256), index=True)
    target_node_id: Mapped[str] = mapped_column(String(256), index=True)
    edge_type: Mapped[str] = mapped_column(String(128), index=True)
    properties: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
