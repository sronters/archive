from __future__ import annotations

from medarchive_document_parsers.pdf import PdfTextParser

from tests.fixtures_pdf import build_text_pdf


def test_pdf_text_parser_extracts_price_lines_with_page_and_bbox() -> None:
    document = build_text_pdf(
        [
            "service resident price KZT nonresident price KZT",
            "MRI brain 25000 32000",
        ]
    )

    parsed = PdfTextParser().parse(document)

    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row.page_number == 1
    assert row.line_number == 2
    assert row.service_name_raw == "MRI brain"
    assert row.resident_price_raw == "25000"
    assert row.nonresident_price_raw == "32000"
    assert row.bbox is not None
