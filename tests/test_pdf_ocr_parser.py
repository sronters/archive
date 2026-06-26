from __future__ import annotations

import pytest
from medarchive_document_parsers.pdf_ocr import OcrTextLine, PdfOcrParser

from tests.fixtures_pdf import build_text_pdf


def test_pdf_ocr_parser_routes_engine_lines_to_canonical_price_rows() -> None:
    parser = PdfOcrParser(ocr_engine=_FakeOcrEngine())

    parsed = parser.parse(build_text_pdf(["scanned placeholder"]))

    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row.service_name_raw == "MRI brain"
    assert row.resident_price_raw == "25000"
    assert row.nonresident_price_raw == "32000"
    assert row.bbox == (10.0, 20.0, 200.0, 40.0)
    assert row.warnings == ("ocr_low_confidence",)


def test_pdf_ocr_parser_requires_configured_engine() -> None:
    parser = PdfOcrParser()

    with pytest.raises(RuntimeError, match="OCR engine is not configured"):
        parser.parse(build_text_pdf(["scanned placeholder"]))


class _FakeOcrEngine:
    engine_name = "fake-ocr"
    engine_version = "test"

    def recognize_pdf_page(self, *, content: bytes, page_number: int) -> tuple[OcrTextLine, ...]:
        assert content.startswith(b"%PDF")
        return (
            OcrTextLine(
                page_number=page_number,
                line_number=1,
                text="service resident price KZT nonresident price KZT",
                bbox=None,
                confidence=1.0,
            ),
            OcrTextLine(
                page_number=page_number,
                line_number=2,
                text="MRI brain 25000 32000",
                bbox=(10.0, 20.0, 200.0, 40.0),
                confidence=0.93,
            ),
        )
