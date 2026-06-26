from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from medarchive_application.document_processing import (
    DocumentProcessingService,
    DocumentToProcess,
)
from medarchive_document_parsers.pdf import ExtractedPdfPriceRow, ParsedPdfDocument
from medarchive_document_parsers.xlsx import ExtractedXlsxPriceRow, ParsedWorkbook
from medarchive_infrastructure.storage import LocalFileStorage

from tests.fakes import FakeDocumentProcessingRepository
from tests.fixtures_docx import build_docx_table
from tests.fixtures_pdf import build_text_pdf
from tests.fixtures_xlsx import build_xlsx


@pytest.mark.asyncio
async def test_document_processing_creates_run_and_extracted_items(tmp_path: Path) -> None:
    document_id = uuid4()
    storage = LocalFileStorage(tmp_path)
    storage_key = "originals/test/price.xlsx"
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    workbook = build_xlsx(
        [
            ["Название услуги", "Цена резидент KZT", "Цена нерезидент KZT"],
            ["МРТ головного мозга", "25000", "32000"],
        ]
    )
    await storage.upload(storage_key, BytesIO(workbook), mime_type)
    repository = FakeDocumentProcessingRepository(
        DocumentToProcess(
            document_id=document_id,
            detected_format="xlsx",
            storage_key=storage_key,
        )
    )
    service = DocumentProcessingService(file_storage=storage, repository=repository)

    result = await service.process_document(document_id)

    assert result.status == "EXTRACTED"
    assert result.extracted_item_count == 1
    assert repository.created_runs[0].document_id == document_id
    assert repository.saved_items[0][1][0].service_name_raw == "МРТ головного мозга"
    assert repository.statuses == [(document_id, "EXTRACTING"), (document_id, "EXTRACTED")]


@pytest.mark.asyncio
async def test_document_processing_supports_docx_tables(tmp_path: Path) -> None:
    document_id = uuid4()
    storage = LocalFileStorage(tmp_path)
    storage_key = "originals/test/price.docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    document = build_docx_table(
        [
            ["service", "resident price KZT", "nonresident price KZT"],
            ["MRI brain", "25000", "32000"],
        ]
    )
    await storage.upload(storage_key, BytesIO(document), mime_type)
    repository = FakeDocumentProcessingRepository(
        DocumentToProcess(
            document_id=document_id,
            detected_format="docx",
            storage_key=storage_key,
        )
    )
    service = DocumentProcessingService(file_storage=storage, repository=repository)

    result = await service.process_document(document_id)

    assert result.status == "EXTRACTED"
    assert result.extracted_item_count == 1
    assert repository.created_runs[0].parser_name == "docx-ooxml-stdlib"
    assert repository.saved_items[0][1][0].service_name_raw == "MRI brain"
    assert repository.saved_items[0][1][0].raw_payload["table_index"] == 1


@pytest.mark.asyncio
async def test_document_processing_supports_legacy_xls_rows(tmp_path: Path) -> None:
    document_id = uuid4()
    storage = LocalFileStorage(tmp_path)
    storage_key = "originals/test/price.xls"
    await storage.upload(storage_key, BytesIO(b"legacy-biff"), "application/vnd.ms-excel")
    repository = FakeDocumentProcessingRepository(
        DocumentToProcess(
            document_id=document_id,
            detected_format="xls",
            storage_key=storage_key,
        )
    )
    service = DocumentProcessingService(
        file_storage=storage,
        repository=repository,
        xls_parser=_FakeXlsParser(),
    )

    result = await service.process_document(document_id)

    assert result.status == "EXTRACTED"
    assert result.extracted_item_count == 1
    assert repository.created_runs[0].parser_name == "xls-xlrd"
    assert repository.saved_items[0][1][0].raw_payload["source"] == "xls"


@pytest.mark.asyncio
async def test_document_processing_supports_text_pdf_rows(tmp_path: Path) -> None:
    document_id = uuid4()
    storage = LocalFileStorage(tmp_path)
    storage_key = "originals/test/price.pdf"
    document = build_text_pdf(
        [
            "service resident price KZT nonresident price KZT",
            "MRI brain 25000 32000",
        ]
    )
    await storage.upload(storage_key, BytesIO(document), "application/pdf")
    repository = FakeDocumentProcessingRepository(
        DocumentToProcess(
            document_id=document_id,
            detected_format="pdf",
            storage_key=storage_key,
        )
    )
    service = DocumentProcessingService(file_storage=storage, repository=repository)

    result = await service.process_document(document_id)

    assert result.status == "EXTRACTED"
    assert result.extracted_item_count == 1
    assert repository.created_runs[0].parser_name == "pdf-pymupdf-text"
    assert repository.saved_items[0][1][0].service_name_raw == "MRI brain"
    assert repository.saved_items[0][1][0].raw_payload["page_number"] == 1


@pytest.mark.asyncio
async def test_document_processing_falls_back_to_ocr_for_scanned_pdf(tmp_path: Path) -> None:
    document_id = uuid4()
    storage = LocalFileStorage(tmp_path)
    storage_key = "originals/test/scanned.pdf"
    await storage.upload(storage_key, BytesIO(build_text_pdf(["image only"])), "application/pdf")
    repository = FakeDocumentProcessingRepository(
        DocumentToProcess(
            document_id=document_id,
            detected_format="pdf",
            storage_key=storage_key,
        )
    )
    service = DocumentProcessingService(
        file_storage=storage,
        repository=repository,
        pdf_parser=_EmptyPdfParser(),
        pdf_ocr_parser=_FakePdfOcrParser(),
    )

    result = await service.process_document(document_id)

    assert result.extracted_item_count == 1
    assert repository.created_runs[0].parser_name == "pdf-ocr-adapter"
    assert repository.saved_items[0][1][0].raw_payload["source"] == "pdf"
    assert repository.saved_items[0][1][0].raw_payload["warnings"] == ["ocr_low_confidence"]


class _FakeXlsParser:
    parser_name = "xls-xlrd"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedWorkbook:
        assert content == b"legacy-biff"
        return ParsedWorkbook(
            rows=(
                ExtractedXlsxPriceRow(
                    sheet_name="Sheet1",
                    row_number=2,
                    service_name_raw="MRI brain",
                    resident_price_raw="25000",
                    nonresident_price_raw="32000",
                    currency_raw="KZT",
                ),
            )
        )


class _EmptyPdfParser:
    parser_name = "pdf-pymupdf-text"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedPdfDocument:
        assert content.startswith(b"%PDF")
        return ParsedPdfDocument(rows=())


class _FakePdfOcrParser:
    parser_name = "pdf-ocr-adapter"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedPdfDocument:
        assert content.startswith(b"%PDF")
        return ParsedPdfDocument(
            rows=(
                ExtractedPdfPriceRow(
                    page_number=1,
                    line_number=1,
                    bbox=(1.0, 2.0, 3.0, 4.0),
                    service_name_raw="MRI brain",
                    resident_price_raw="25000",
                    nonresident_price_raw="32000",
                    currency_raw="KZT",
                    warnings=("ocr_low_confidence",),
                ),
            )
        )
