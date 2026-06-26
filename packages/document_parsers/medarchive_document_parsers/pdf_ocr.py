from __future__ import annotations

import base64
import importlib
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

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


class HttpOcrEngine:
    engine_name = "http-ocr"
    engine_version = "0.1.0"

    def __init__(self, *, endpoint_url: str, bearer_token: str | None = None) -> None:
        self._endpoint_url = endpoint_url
        self._bearer_token = bearer_token

    def recognize_pdf_page(self, *, content: bytes, page_number: int) -> tuple[OcrTextLine, ...]:
        image = _render_page_png(content=content, page_number=page_number)
        payload = json.dumps(
            {
                "page_number": page_number,
                "image_base64": base64.b64encode(image).decode("ascii"),
                "language_hints": ["ru", "kk", "en"],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        request = Request(self._endpoint_url, data=payload, headers=headers, method="POST")
        with urlopen(request, timeout=60) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        return _parse_http_ocr_lines(response_payload, page_number=page_number)


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


def _render_page_png(*, content: bytes, page_number: int) -> bytes:
    fitz = importlib.import_module("fitz")
    document = fitz.open(stream=content, filetype="pdf")
    try:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(dpi=220)
        return bytes(pixmap.tobytes("png"))
    finally:
        document.close()


def _parse_http_ocr_lines(payload: object, *, page_number: int) -> tuple[OcrTextLine, ...]:
    if not isinstance(payload, dict):
        raise ValueError("OCR response must be a JSON object.")
    rows = payload.get("lines")
    if not isinstance(rows, list):
        raise ValueError("OCR response must contain a lines array.")
    parsed: list[OcrTextLine] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError("OCR line must be a JSON object.")
        text = row.get("text")
        confidence = row.get("confidence", 0)
        if not isinstance(text, str):
            raise ValueError("OCR line text must be a string.")
        if not isinstance(confidence, int | float):
            raise ValueError("OCR line confidence must be numeric.")
        parsed.append(
            OcrTextLine(
                page_number=page_number,
                line_number=_int_or_default(row.get("line_number"), index),
                text=text,
                bbox=_bbox(row.get("bbox")),
                confidence=float(confidence),
            )
        )
    return tuple(parsed)


def _int_or_default(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _bbox(value: object) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple) or len(value) != 4:
        raise ValueError("OCR bbox must contain four numeric values.")
    if not all(isinstance(item, int | float) for item in value):
        raise ValueError("OCR bbox values must be numeric.")
    return (
        float(value[0]),
        float(value[1]),
        float(value[2]),
        float(value[3]),
    )
