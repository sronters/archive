from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from medarchive_document_parsers.docx import DocxParser
from medarchive_document_parsers.pdf import PdfTextParser
from medarchive_document_parsers.xls import XlsParser
from medarchive_document_parsers.xlsx import ParsedWorkbook, XlsxParser
from medarchive_domain.ports import FileStorage

from medarchive_application.review_preparation import ReviewPreparationService


@dataclass(frozen=True)
class ProcessingRunDraft:
    document_id: UUID
    pipeline_version: str
    parser_name: str
    parser_version: str
    status: str


@dataclass(frozen=True)
class ExtractedItemDraft:
    sheet_name: str | None
    row_number: int | None
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None
    extraction_confidence: float | None
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class DocumentToProcess:
    document_id: UUID
    detected_format: str
    storage_key: str


@dataclass(frozen=True)
class DocumentProcessingResult:
    document_id: UUID
    processing_run_id: UUID
    extracted_item_count: int
    review_task_count: int
    status: str


class DocumentProcessingRepository(Protocol):
    def get_document_to_process(self, document_id: UUID) -> DocumentToProcess:
        ...

    def create_processing_run(self, draft: ProcessingRunDraft) -> UUID:
        ...

    def save_extracted_items(
        self,
        *,
        processing_run_id: UUID,
        items: tuple[ExtractedItemDraft, ...],
    ) -> None:
        ...

    def mark_document_status(self, *, document_id: UUID, status: str) -> None:
        ...


class WorkbookParser(Protocol):
    parser_name: str
    parser_version: str

    def parse(self, content: bytes) -> ParsedWorkbook:
        ...


class DocumentProcessingService:
    pipeline_version = "document-processing-0.1.0"

    def __init__(
        self,
        *,
        file_storage: FileStorage,
        repository: DocumentProcessingRepository,
        review_preparation_service: ReviewPreparationService | None = None,
        xlsx_parser: WorkbookParser | None = None,
        xls_parser: WorkbookParser | None = None,
        docx_parser: DocxParser | None = None,
        pdf_parser: PdfTextParser | None = None,
    ) -> None:
        self._file_storage = file_storage
        self._repository = repository
        self._review_preparation_service = review_preparation_service
        self._xlsx_parser = xlsx_parser or XlsxParser()
        self._xls_parser = xls_parser or XlsParser()
        self._docx_parser = docx_parser or DocxParser()
        self._pdf_parser = pdf_parser or PdfTextParser()

    async def process_document(self, document_id: UUID) -> DocumentProcessingResult:
        document = self._repository.get_document_to_process(document_id)
        if document.detected_format not in {"xlsx", "xls", "docx", "pdf"}:
            self._repository.mark_document_status(document_id=document_id, status="PERMANENT_ERROR")
            raise ValueError(f"Unsupported worker format in this phase: {document.detected_format}")

        content = await self._file_storage.download(document.storage_key)
        parser_name, parser_version, drafts = self._extract_drafts(
            detected_format=document.detected_format,
            content=content,
        )
        self._repository.mark_document_status(document_id=document_id, status="EXTRACTING")
        processing_run_id = self._repository.create_processing_run(
            ProcessingRunDraft(
                document_id=document_id,
                pipeline_version=self.pipeline_version,
                parser_name=parser_name,
                parser_version=parser_version,
                status="started",
            )
        )
        self._repository.save_extracted_items(
            processing_run_id=processing_run_id,
            items=drafts,
        )
        self._repository.mark_document_status(document_id=document_id, status="EXTRACTED")
        review_task_count = 0
        status = "EXTRACTED"
        if self._review_preparation_service is not None:
            review_result = self._review_preparation_service.prepare_run(processing_run_id)
            review_task_count = review_result.review_task_count
            status = review_result.document_status
        return DocumentProcessingResult(
            document_id=document_id,
            processing_run_id=processing_run_id,
            extracted_item_count=len(drafts),
            review_task_count=review_task_count,
            status=status,
        )

    def _extract_drafts(
        self,
        *,
        detected_format: str,
        content: bytes,
    ) -> tuple[str, str, tuple[ExtractedItemDraft, ...]]:
        if detected_format == "xlsx":
            parsed = self._xlsx_parser.parse(content)
            return (
                self._xlsx_parser.parser_name,
                self._xlsx_parser.parser_version,
                tuple(
                    ExtractedItemDraft(
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        service_name_raw=row.service_name_raw,
                        resident_price_raw=row.resident_price_raw,
                        nonresident_price_raw=row.nonresident_price_raw,
                        currency_raw=row.currency_raw,
                        extraction_confidence=None,
                        raw_payload={"warnings": list(row.warnings), "source": "xlsx"},
                    )
                    for row in parsed.rows
                ),
            )
        if detected_format == "xls":
            parsed_xls = self._xls_parser.parse(content)
            return (
                self._xls_parser.parser_name,
                self._xls_parser.parser_version,
                tuple(
                    ExtractedItemDraft(
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        service_name_raw=row.service_name_raw,
                        resident_price_raw=row.resident_price_raw,
                        nonresident_price_raw=row.nonresident_price_raw,
                        currency_raw=row.currency_raw,
                        extraction_confidence=None,
                        raw_payload={"warnings": list(row.warnings), "source": "xls"},
                    )
                    for row in parsed_xls.rows
                ),
            )
        if detected_format == "docx":
            parsed_docx = self._docx_parser.parse(content)
            return (
                self._docx_parser.parser_name,
                self._docx_parser.parser_version,
                tuple(
                    ExtractedItemDraft(
                        sheet_name=None,
                        row_number=row.row_number,
                        service_name_raw=row.service_name_raw,
                        resident_price_raw=row.resident_price_raw,
                        nonresident_price_raw=row.nonresident_price_raw,
                        currency_raw=row.currency_raw,
                        extraction_confidence=None,
                        raw_payload={
                            "warnings": list(row.warnings),
                            "source": "docx",
                            "table_index": row.table_index,
                        },
                    )
                    for row in parsed_docx.rows
                ),
            )
        parsed_pdf = self._pdf_parser.parse(content)
        return (
            self._pdf_parser.parser_name,
            self._pdf_parser.parser_version,
            tuple(
                ExtractedItemDraft(
                    sheet_name=None,
                    row_number=row.line_number,
                    service_name_raw=row.service_name_raw,
                    resident_price_raw=row.resident_price_raw,
                    nonresident_price_raw=row.nonresident_price_raw,
                    currency_raw=row.currency_raw,
                    extraction_confidence=None,
                    raw_payload={
                        "warnings": list(row.warnings),
                        "source": "pdf",
                        "page_number": row.page_number,
                        "bbox": list(row.bbox) if row.bbox is not None else None,
                    },
                )
                for row in parsed_pdf.rows
            ),
        )
