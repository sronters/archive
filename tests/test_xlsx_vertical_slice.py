from __future__ import annotations

from datetime import date
from uuid import uuid4

from medarchive_application.xlsx_vertical_slice import XlsxVerticalSliceProcessor
from medarchive_document_parsers.xlsx import XlsxParser
from medarchive_matching.simple_matcher import CatalogService

from tests.fixtures_xlsx import build_xlsx


def test_xlsx_parser_extracts_price_rows_with_sheet_and_row_provenance() -> None:
    workbook = build_xlsx(
        [
            ["ignored", "ignored", "ignored"],
            ["Название услуги", "Цена резидент KZT", "Цена нерезидент KZT"],
            ["МРТ головного мозга", "25000", "32000"],
        ]
    )

    parsed = XlsxParser().parse(workbook)

    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row.sheet_name == "Прайс"
    assert row.row_number == 3
    assert row.service_name_raw == "МРТ головного мозга"
    assert row.resident_price_raw == "25000"
    assert row.nonresident_price_raw == "32000"


def test_xlsx_vertical_slice_auto_accepts_exact_service_and_valid_prices() -> None:
    service_id = uuid4()
    partner_id = uuid4()
    workbook = build_xlsx(
        [
            ["Название услуги", "Цена резидент KZT", "Цена нерезидент KZT"],
            ["МРТ головного мозга", "25000", "32000"],
        ]
    )

    result = XlsxVerticalSliceProcessor().process(
        workbook_content=workbook,
        catalog=[
            CatalogService(
                service_id=service_id,
                external_service_id="svc-001",
                official_name="МРТ головного мозга",
            )
        ],
        partner_id=partner_id,
        effective_date=date(2026, 6, 26),
    )

    assert result.auto_accepted_count == 1
    assert result.review_task_count == 0
    assert result.rows[0].accepted_service_id == service_id
    assert result.rows[0].resident_price_kzt is not None
    assert str(result.rows[0].resident_price_kzt) == "25000"


def test_xlsx_vertical_slice_auto_accepts_exact_source_code() -> None:
    service_id = uuid4()
    partner_id = uuid4()
    workbook = build_xlsx(
        [
            ["service", "price"],
            ["svc-001", "25000"],
        ]
    )

    result = XlsxVerticalSliceProcessor().process(
        workbook_content=workbook,
        catalog=[
            CatalogService(
                service_id=service_id,
                external_service_id="svc-001",
                official_name="РњР Рў РіРѕР»РѕРІРЅРѕРіРѕ РјРѕР·РіР°",
            )
        ],
        partner_id=partner_id,
        effective_date=date(2026, 6, 26),
    )

    assert result.auto_accepted_count == 1
    assert result.rows[0].accepted_service_id == service_id
    assert result.rows[0].match_candidates[0].retrieval_method == "source_code"


def test_xlsx_vertical_slice_routes_uncertain_match_to_review() -> None:
    workbook = build_xlsx(
        [
            ["Название услуги", "Цена резидент KZT"],
            ["Неизвестная услуга", "1000"],
        ]
    )

    result = XlsxVerticalSliceProcessor().process(
        workbook_content=workbook,
        catalog=[
            CatalogService(
                service_id=uuid4(),
                external_service_id="svc-001",
                official_name="МРТ головного мозга",
            )
        ],
    )

    assert result.review_task_count == 1
    assert "service_match_uncertain" in result.rows[0].review_reasons
    assert "partner_unresolved" in result.rows[0].review_reasons
