from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from medarchive_domain.ids import new_id
from medarchive_domain.workflow import DocumentWorkflowState


@dataclass
class Partner:
    name: str
    external_partner_id: str | None = None
    id: UUID = field(default_factory=new_id)
    bin: str | None = None
    city: str | None = None
    is_active: bool = True


@dataclass
class Service:
    official_name: str
    external_service_id: str | None = None
    id: UUID = field(default_factory=new_id)
    category: str | None = None
    synonyms: tuple[str, ...] = ()
    is_active: bool = True


@dataclass
class IngestionBatch:
    source: str
    uploaded_by: UUID | None = None
    id: UUID = field(default_factory=new_id)
    status: str = "created"
    documents_total: int = 0
    documents_processed: int = 0
    documents_failed: int = 0


@dataclass
class SourceFile:
    batch_id: UUID
    original_filename: str
    detected_mime_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    id: UUID = field(default_factory=new_id)
    malware_scan_status: str = "pending"


@dataclass
class PriceDocument:
    source_file_id: UUID
    partner_id: UUID | None = None
    id: UUID = field(default_factory=new_id)
    external_source_id: str | None = None
    effective_date: date | None = None
    detected_format: str | None = None
    status: DocumentWorkflowState = DocumentWorkflowState.UPLOADED


@dataclass
class ProcessingRun:
    document_id: UUID
    pipeline_version: str
    parser_name: str
    parser_version: str
    matcher_version: str | None = None
    id: UUID = field(default_factory=new_id)
    status: str = "started"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_details: str | None = None


@dataclass
class ExtractedPriceItem:
    processing_run_id: UUID
    service_name_raw: str
    id: UUID = field(default_factory=new_id)
    page_number: int | None = None
    sheet_name: str | None = None
    row_number: int | None = None
    source_bbox: tuple[float, float, float, float] | None = None
    service_code_raw: str | None = None
    resident_price_raw: str | None = None
    nonresident_price_raw: str | None = None
    currency_raw: str | None = None
    extraction_confidence: float | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)


@dataclass
class ServiceMatch:
    extracted_item_id: UUID
    service_id: UUID
    retrieval_method: str
    matcher_version: str
    rank: int
    id: UUID = field(default_factory=new_id)
    retrieval_score: float | None = None
    reranker_score: float | None = None


@dataclass
class ReviewTask:
    extracted_item_id: UUID
    reason: str
    id: UUID = field(default_factory=new_id)
    priority: int = 0
    status: str = "open"
    assigned_to: UUID | None = None
    version: int = 0


@dataclass
class PriceVersion:
    partner_id: UUID
    service_id: UUID
    source_document_id: UUID
    resident_price_kzt: Decimal | None
    nonresident_price_kzt: Decimal | None
    valid_from: date
    id: UUID = field(default_factory=new_id)
    original_price: Decimal | None = None
    original_currency: str | None = None
    exchange_rate: Decimal | None = None
    valid_to: date | None = None
    published_at: datetime | None = None
    verification_status: str = "draft"
    superseded_by: UUID | None = None


@dataclass
class AuditEvent:
    action: str
    entity_type: str
    entity_id: UUID
    actor_type: str
    id: UUID = field(default_factory=new_id)
    actor_id: UUID | None = None
    before_json: dict[str, object] | None = None
    after_json: dict[str, object] | None = None
    request_id: str | None = None
    ip_address: str | None = None


@dataclass
class OutboxEvent:
    event_type: str
    payload: dict[str, object]
    id: UUID = field(default_factory=new_id)
    event_version: int = 1
    published_at: datetime | None = None
    attempts: int = 0
