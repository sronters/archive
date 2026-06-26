"""Pure MedArchive domain package.

This package must not import infrastructure frameworks such as Celery, Redis,
MinIO clients, FastAPI, or company-specific API clients.
"""

from medarchive_domain.canonical import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    ExtractionConfidence,
    ParserMetadata,
    SourceProvenance,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
)
from medarchive_domain.entities import (
    AuditEvent,
    ExtractedPriceItem,
    IngestionBatch,
    OutboxEvent,
    Partner,
    PriceDocument,
    PriceVersion,
    ProcessingRun,
    ReviewTask,
    Service,
    ServiceMatch,
    SourceFile,
)
from medarchive_domain.errors import DomainErrorCode
from medarchive_domain.workflow import DocumentWorkflowState, transition_document_state

__all__ = [
    "AuditEvent",
    "BoundingBox",
    "CanonicalDocument",
    "CanonicalPage",
    "DocumentWorkflowState",
    "DomainErrorCode",
    "ExtractedPriceItem",
    "ExtractionConfidence",
    "IngestionBatch",
    "OutboxEvent",
    "ParserMetadata",
    "Partner",
    "PriceDocument",
    "PriceVersion",
    "ProcessingRun",
    "ReviewTask",
    "Service",
    "ServiceMatch",
    "SourceFile",
    "SourceProvenance",
    "TableBlock",
    "TableCell",
    "TableRow",
    "TextBlock",
    "transition_document_state",
]
