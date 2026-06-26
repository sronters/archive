from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from medarchive_application.document_processing import (
    DocumentProcessingRepository,
    DocumentToProcess,
    ExtractedItemDraft,
    ProcessingRunDraft,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    ExtractedPriceItemModel,
    PriceDocumentModel,
    ProcessingRunModel,
    SourceFileModel,
)


class SqlAlchemyDocumentProcessingRepository(DocumentProcessingRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_document_to_process(self, document_id: UUID) -> DocumentToProcess:
        with self._session_factory() as session:
            statement = (
                select(PriceDocumentModel, SourceFileModel)
                .join(SourceFileModel, PriceDocumentModel.source_file_id == SourceFileModel.id)
                .where(PriceDocumentModel.id == document_id)
            )
            row = session.execute(statement).one_or_none()
            if row is None:
                raise LookupError(f"Document not found: {document_id}")
            document, source_file = row
            if document.detected_format is None:
                raise ValueError(f"Document has no detected format: {document_id}")
            return DocumentToProcess(
                document_id=document.id,
                detected_format=document.detected_format,
                storage_key=source_file.storage_key,
            )

    def create_processing_run(self, draft: ProcessingRunDraft) -> UUID:
        processing_run_id = uuid4()
        with self._session_factory() as session:
            run = ProcessingRunModel(
                id=processing_run_id,
                document_id=draft.document_id,
                pipeline_version=draft.pipeline_version,
                parser_name=draft.parser_name,
                parser_version=draft.parser_version,
                matcher_version=None,
                status=draft.status,
                started_at=datetime.now(timezone.utc),  # noqa: UP017
            )
            session.add(run)
            session.commit()
        return processing_run_id

    def save_extracted_items(
        self,
        *,
        processing_run_id: UUID,
        items: tuple[ExtractedItemDraft, ...],
    ) -> None:
        with self._session_factory() as session:
            session.add_all(
                [
                    ExtractedPriceItemModel(
                        id=uuid4(),
                        processing_run_id=processing_run_id,
                        sheet_name=item.sheet_name,
                        row_number=item.row_number,
                        service_name_raw=item.service_name_raw,
                        resident_price_raw=item.resident_price_raw,
                        nonresident_price_raw=item.nonresident_price_raw,
                        currency_raw=item.currency_raw,
                        extraction_confidence=item.extraction_confidence,
                        raw_payload=item.raw_payload,
                    )
                    for item in items
                ]
            )
            session.commit()

    def mark_document_status(self, *, document_id: UUID, status: str) -> None:
        with self._session_factory() as session:
            document = session.get(PriceDocumentModel, document_id)
            if document is None:
                raise LookupError(f"Document not found: {document_id}")
            document.status = status
            session.commit()
