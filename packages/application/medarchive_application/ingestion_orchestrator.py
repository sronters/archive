from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from medarchive_application.ingestion import IngestionBatchResult, IngestionService

DOCUMENT_PROCESSING_REQUESTED = "document.processing_requested"


@dataclass(frozen=True)
class RecordedDocument:
    document_id: UUID
    source_file_id: UUID
    original_filename: str
    storage_key: str
    detected_format: str


@dataclass(frozen=True)
class RecordedIngestionBatch:
    batch_id: UUID
    documents: tuple[RecordedDocument, ...]
    outbox_event_count: int


class IngestionRecorder(Protocol):
    def record_ingestion(self, result: IngestionBatchResult) -> RecordedIngestionBatch:
        ...


class IngestionOrchestrator:
    def __init__(
        self,
        *,
        ingestion_service: IngestionService,
        ingestion_recorder: IngestionRecorder,
    ) -> None:
        self._ingestion_service = ingestion_service
        self._ingestion_recorder = ingestion_recorder

    async def ingest_files(
        self,
        files: list[tuple[str, bytes]],
        *,
        idempotency_key: str | None = None,
    ) -> tuple[IngestionBatchResult, RecordedIngestionBatch]:
        inspected = await self._ingestion_service.ingest_files(
            files,
            idempotency_key=idempotency_key,
        )
        recorded = self._ingestion_recorder.record_ingestion(inspected)
        return inspected, recorded

    async def ingest_file_streams(
        self,
        files: list[tuple[str, BinaryIO]],
        *,
        idempotency_key: str | None = None,
    ) -> tuple[IngestionBatchResult, RecordedIngestionBatch]:
        inspected = await self._ingestion_service.ingest_file_streams(
            files,
            idempotency_key=idempotency_key,
        )
        recorded = self._ingestion_recorder.record_ingestion(inspected)
        return inspected, recorded
