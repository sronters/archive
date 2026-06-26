from __future__ import annotations

from uuid import uuid4

from medarchive_application.ingestion import IngestionBatchResult
from medarchive_application.ingestion_orchestrator import (
    DOCUMENT_PROCESSING_REQUESTED,
    RecordedDocument,
    RecordedIngestionBatch,
)
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    IngestionBatchModel,
    OutboxEventModel,
    PriceDocumentModel,
    SourceFileModel,
)


class SqlAlchemyIngestionRecorder:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_ingestion(self, result: IngestionBatchResult) -> RecordedIngestionBatch:
        with self._session_factory() as session:
            try:
                recorded = self._record_with_session(session, result)
                session.commit()
                return recorded
            except Exception:
                session.rollback()
                raise

    def _record_with_session(
        self,
        session: Session,
        result: IngestionBatchResult,
    ) -> RecordedIngestionBatch:
        batch = IngestionBatchModel(
            id=result.batch_id,
            source="api_upload",
            uploaded_by=None,
            status=result.status,
            documents_total=result.accepted_documents_count + result.rejected_documents_count,
            documents_processed=0,
            documents_failed=result.rejected_documents_count,
        )
        session.add(batch)

        documents: list[RecordedDocument] = []
        for accepted in result.accepted_files:
            source_file_id = uuid4()
            document_id = uuid4()
            source_file = SourceFileModel(
                id=source_file_id,
                batch_id=result.batch_id,
                original_filename=accepted.original_filename,
                detected_mime_type=accepted.detected_mime_type,
                size_bytes=accepted.size_bytes,
                sha256=accepted.sha256,
                storage_key=accepted.storage_key,
                malware_scan_status=accepted.malware_scan_status,
            )
            document = PriceDocumentModel(
                id=document_id,
                source_file_id=source_file_id,
                detected_format=accepted.detected_format,
                status="UPLOADED",
            )
            outbox_event = OutboxEventModel(
                event_type=DOCUMENT_PROCESSING_REQUESTED,
                event_version=1,
                payload={
                    "document_id": str(document_id),
                    "batch_id": str(result.batch_id),
                    "source_file_id": str(source_file_id),
                    "detected_format": accepted.detected_format,
                    "storage_key": accepted.storage_key,
                },
            )
            session.add_all([source_file, document, outbox_event])
            documents.append(
                RecordedDocument(
                    document_id=document_id,
                    source_file_id=source_file_id,
                    original_filename=accepted.original_filename,
                    storage_key=accepted.storage_key,
                    detected_format=accepted.detected_format,
                )
            )

        return RecordedIngestionBatch(
            batch_id=result.batch_id,
            documents=tuple(documents),
            outbox_event_count=len(documents),
        )
