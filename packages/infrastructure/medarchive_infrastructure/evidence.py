from __future__ import annotations

from uuid import UUID

from medarchive_application.evidence import PriceEvidence
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    ExtractedPriceItemModel,
    PriceDocumentModel,
    ProcessingRunModel,
    SourceFileModel,
)


class SqlAlchemyEvidenceRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_price_evidence(self, extracted_item_id: UUID) -> PriceEvidence:
        with self._session_factory() as session:
            statement = (
                select(
                    ExtractedPriceItemModel,
                    ProcessingRunModel,
                    PriceDocumentModel,
                    SourceFileModel,
                )
                .join(
                    ProcessingRunModel,
                    ProcessingRunModel.id == ExtractedPriceItemModel.processing_run_id,
                )
                .join(PriceDocumentModel, PriceDocumentModel.id == ProcessingRunModel.document_id)
                .join(SourceFileModel, SourceFileModel.id == PriceDocumentModel.source_file_id)
                .where(ExtractedPriceItemModel.id == extracted_item_id)
            )
            row = session.execute(statement).one_or_none()
            if row is None:
                raise LookupError(f"Extracted item not found: {extracted_item_id}")
            item, run, document, source_file = row
            return PriceEvidence(
                extracted_item_id=item.id,
                document_id=document.id,
                source_file_id=source_file.id,
                original_filename=source_file.original_filename,
                storage_key=source_file.storage_key,
                sha256=source_file.sha256,
                parser_name=run.parser_name,
                parser_version=run.parser_version,
                pipeline_version=run.pipeline_version,
                processing_run_id=run.id,
                page_number=item.page_number,
                sheet_name=item.sheet_name,
                row_number=item.row_number,
                source_bbox=item.source_bbox,
                service_name_raw=item.service_name_raw,
                resident_price_raw=item.resident_price_raw,
                nonresident_price_raw=item.nonresident_price_raw,
                currency_raw=item.currency_raw,
                extraction_confidence=item.extraction_confidence,
                raw_payload=item.raw_payload,
            )
