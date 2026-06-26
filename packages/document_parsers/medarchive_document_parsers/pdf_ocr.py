from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Protocol

from medarchive_document_parsers.pdf import (
    ExtractedPdfPriceRow,
    ParsedPdfDocument,
    _detect_currency,
    _parse_price_line,
)


@dataclass(frozen=True)
class OcrTextLine:
    page_number: int
    line_number: int
    text: str
    bbox: tuple[float, float, float, float] | None
    confidence: float


class OcrEngine(Protocol):
    engine_name: str
    engine_version: str

    def recognize_pdf_page(self, *, content: bytes, page_number: int) -> tuple[OcrTextLine, ...]:
        ...


class NotConfiguredOcrEngine:
    engine_name = "not-configured"
    engine_version = "0"

    def recognize_pdf_page(self, *, content: bytes, page_number: int) -> tuple[OcrTextLine, ...]:
        raise RuntimeError(
            "OCR engine is not configured. Install a deployment-approved OCR adapter before "
            "processing scanned PDFs.",
        )


class PdfOcrParser:
    parser_name = "pdf-ocr-adapter"
    parser_version = "0.1.0"

    def __init__(self, *, ocr_engine: OcrEngine | None = None) -> None:
        self._ocr_engine = ocr_engine or NotConfiguredOcrEngine()

    def parse(self, content: bytes) -> ParsedPdfDocument:
        fitz = importlib.import_module("fitz")
        document = fitz.open(stream=content, filetype="pdf")
        extracted: list[ExtractedPdfPriceRow] = []
        warnings: list[str] = []
        try:
            page_count = document.page_count
        finally:
            document.close()

        for page_number in range(1, page_count + 1):
            lines = self._ocr_engine.recognize_pdf_page(content=content, page_number=page_number)
            page_rows = _rows_from_ocr_lines(lines)
            if not page_rows:
                warnings.append(f"page {page_number}: OCR produced no price rows")
            extracted.extend(page_rows)
        return ParsedPdfDocument(rows=tuple(extracted), warnings=tuple(warnings))


def _rows_from_ocr_lines(lines: tuple[OcrTextLine, ...]) -> list[ExtractedPdfPriceRow]:
    rows: list[ExtractedPdfPriceRow] = []
    for line in lines:
        parsed = _parse_price_line(line.text)
        if parsed is None:
            continue
        service, resident, nonresident = parsed
        warnings = ("ocr_low_confidence",) if line.confidence < 0.98 else ()
        rows.append(
            ExtractedPdfPriceRow(
                page_number=line.page_number,
                line_number=line.line_number,
                bbox=line.bbox,
                service_name_raw=service,
                resident_price_raw=resident,
                nonresident_price_raw=nonresident,
                currency_raw=_detect_currency(line.text),
                warnings=warnings,
            )
        )
    return rows
