from __future__ import annotations

from typing import Any

from medarchive_document_parsers.xlsx import (
    ExtractedXlsxPriceRow,
    ParsedWorkbook,
    _cell,
    _cell_optional,
    _detect_columns,
    _detect_currency,
    _detect_header_row,
)


class XlsParser:
    parser_name = "xls-xlrd"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedWorkbook:
        try:
            import xlrd
        except ImportError as exc:  # pragma: no cover - depends on optional parser extra
            raise RuntimeError(
                "Legacy XLS parsing requires the 'xlrd' package from the parser extras.",
            ) from exc

        workbook = xlrd.open_workbook(file_contents=content, formatting_info=False)
        extracted: list[ExtractedXlsxPriceRow] = []
        warnings: list[str] = []
        for sheet in workbook.sheets():
            table = _sheet_table(sheet)
            header_index = _detect_header_row(table)
            if header_index is None:
                warnings.append(f"{sheet.name}: header row not detected")
                continue
            columns = _detect_columns(table[header_index])
            if columns.service_index is None:
                warnings.append(f"{sheet.name}: service column not detected")
                continue
            for row_index, row in enumerate(table[header_index + 1 :], start=header_index + 2):
                service = _cell(row, columns.service_index).strip()
                if not service:
                    continue
                resident = _cell_optional(row, columns.resident_price_index)
                nonresident = _cell_optional(row, columns.nonresident_price_index)
                if resident is None and nonresident is None:
                    continue
                extracted.append(
                    ExtractedXlsxPriceRow(
                        sheet_name=sheet.name,
                        row_number=row_index,
                        service_name_raw=service,
                        resident_price_raw=resident,
                        nonresident_price_raw=nonresident,
                        currency_raw=_detect_currency(resident, nonresident),
                    )
                )
        return ParsedWorkbook(rows=tuple(extracted), warnings=tuple(warnings))


def _sheet_table(sheet: Any) -> list[list[str]]:
    return [
        [
            _cell_value(sheet.cell_value(row_index, column_index))
            for column_index in range(sheet.ncols)
        ]
        for row_index in range(sheet.nrows)
    ]


def _cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
