from __future__ import annotations

from medarchive_document_parsers.docx import DocxParser

from tests.fixtures_docx import build_docx_table


def test_docx_parser_extracts_table_price_rows_with_provenance() -> None:
    document = build_docx_table(
        [
            ["service", "resident price KZT", "nonresident price KZT"],
            ["MRI brain", "25000", "32000"],
        ]
    )

    parsed = DocxParser().parse(document)

    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row.table_index == 1
    assert row.row_number == 2
    assert row.service_name_raw == "MRI brain"
    assert row.resident_price_raw == "25000"
    assert row.nonresident_price_raw == "32000"
