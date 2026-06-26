from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from uuid import UUID
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from medarchive_application.price_versions import PriceVersionRead

EXPORT_COLUMNS = (
    "price_version_id",
    "partner_id",
    "external_partner_id",
    "partner_name",
    "service_id",
    "external_service_id",
    "service_name",
    "resident_price_kzt",
    "nonresident_price_kzt",
    "original_price",
    "original_currency",
    "valid_from",
    "valid_to",
    "published_at",
    "source_document_id",
    "external_source_id",
    "source_file_name",
    "source_sheet",
    "source_page",
    "source_row",
)


@dataclass(frozen=True)
class ExportedFile:
    filename: str
    media_type: str
    content: bytes


class PriceVersionExportService:
    def export_price_versions(
        self,
        rows: tuple[PriceVersionRead, ...],
        *,
        export_format: str,
    ) -> ExportedFile:
        normalized_format = export_format.casefold()
        export_rows = [_row_dict(row) for row in rows]
        if normalized_format == "json":
            return ExportedFile(
                filename="price-versions.json",
                media_type="application/json",
                content=json.dumps(export_rows, ensure_ascii=False, indent=2).encode("utf-8"),
            )
        if normalized_format == "csv":
            return ExportedFile(
                filename="price-versions.csv",
                media_type="text/csv; charset=utf-8",
                content=_csv_bytes(export_rows),
            )
        if normalized_format == "xlsx":
            return ExportedFile(
                filename="price-versions.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=_xlsx_bytes(export_rows),
            )
        raise ValueError(f"Unsupported export format: {export_format}")


def _row_dict(row: PriceVersionRead) -> dict[str, str | None]:
    values: dict[str, object | None] = {
        "price_version_id": row.price_version_id,
        "partner_id": row.partner_id,
        "external_partner_id": row.external_partner_id,
        "partner_name": row.partner_name,
        "service_id": row.service_id,
        "external_service_id": row.external_service_id,
        "service_name": row.service_name,
        "resident_price_kzt": row.resident_price_kzt,
        "nonresident_price_kzt": row.nonresident_price_kzt,
        "original_price": row.original_price,
        "original_currency": row.original_currency,
        "valid_from": row.valid_from,
        "valid_to": row.valid_to,
        "published_at": row.published_at,
        "source_document_id": row.source_document_id,
        "external_source_id": row.external_source_id,
        "source_file_name": None,
        "source_sheet": None,
        "source_page": None,
        "source_row": None,
    }
    return {key: _export_value(values[key]) for key in EXPORT_COLUMNS}


def _export_value(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _csv_bytes(rows: list[dict[str, str | None]]) -> bytes:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(EXPORT_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row[key] or "" for key in EXPORT_COLUMNS})
    return buffer.getvalue().encode("utf-8-sig")


def _xlsx_bytes(rows: list[dict[str, str | None]]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml"
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml"
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
                Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="price_versions" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows))
    return buffer.getvalue()


def _worksheet_xml(rows: list[dict[str, str | None]]) -> str:
    table = [list(EXPORT_COLUMNS)]
    table.extend([[row[column] or "" for column in EXPORT_COLUMNS] for row in rows])
    row_xml = []
    for row_index, values in enumerate(table, start=1):
        cells = []
        for column_index, value in enumerate(values):
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(row_xml)}</sheetData>
</worksheet>"""


def _column_name(index: int) -> str:
    value = index + 1
    letters = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters
