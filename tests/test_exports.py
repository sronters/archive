from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from medarchive_application.exports import PriceVersionExportService

from tests.fakes import FakePriceVersionRepository


def test_price_version_export_service_generates_csv_with_required_columns() -> None:
    rows = FakePriceVersionRepository().rows

    exported = PriceVersionExportService().export_price_versions(rows, export_format="csv")

    assert exported.filename == "price-versions.csv"
    content = exported.content.decode("utf-8-sig")
    assert "price_version_id,partner_id,external_partner_id,partner_name" in content
    assert "clinic-001" in content
    assert "Medical Center" in content


def test_price_version_export_service_generates_xlsx_workbook() -> None:
    rows = FakePriceVersionRepository().rows

    exported = PriceVersionExportService().export_price_versions(rows, export_format="xlsx")

    assert exported.filename == "price-versions.xlsx"
    with ZipFile(BytesIO(exported.content)) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "external_partner_id" in sheet
    assert "clinic-001" in sheet
