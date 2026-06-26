from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

NONRESIDENT_TOKEN = "\u043d\u0435\u0440\u0435\u0437\u0438\u0434\u0435\u043d\u0442"
SERVICE_HEADER_TOKENS = (
    "\u0443\u0441\u043b\u0443\u0433",
    "service",
    "\u043d\u0430\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d",
    "\u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
)
PRICE_HEADER_TOKENS = (
    "\u0446\u0435\u043d\u0430",
    "price",
    "\u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c",
    "kzt",
    "\u0442\u0435\u043d\u0433\u0435",
)
KZT_SYMBOL = "\u20b8"
TENGE_WORD = "\u0442\u0435\u043d\u0433\u0435"


@dataclass(frozen=True)
class ExtractedXlsxPriceRow:
    sheet_name: str
    row_number: int
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedWorkbook:
    rows: tuple[ExtractedXlsxPriceRow, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _SheetRow:
    row_number: int
    cells: list[str]


class XlsxParser:
    parser_name = "xlsx-stdlib"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedWorkbook:
        with ZipFile(BytesIO(content)) as workbook:
            shared_strings = _read_shared_strings(workbook)
            sheets = _read_sheets(workbook)
            extracted: list[ExtractedXlsxPriceRow] = []
            warnings: list[str] = []
            for sheet_name, sheet_path in sheets:
                table = _read_sheet_table(workbook, sheet_path, shared_strings)
                header_index = _detect_header_row(table)
                if header_index is None:
                    warnings.append(f"{sheet_name}: header row not detected")
                    continue
                columns = _detect_columns(table[header_index].cells)
                if columns.service_index is None:
                    warnings.append(f"{sheet_name}: service column not detected")
                    continue
                for sheet_row in table[header_index + 1 :]:
                    service = _cell(sheet_row.cells, columns.service_index).strip()
                    if not service:
                        continue
                    resident = _cell_optional(sheet_row.cells, columns.resident_price_index)
                    nonresident = _cell_optional(sheet_row.cells, columns.nonresident_price_index)
                    if resident is None and nonresident is None:
                        continue
                    extracted.append(
                        ExtractedXlsxPriceRow(
                            sheet_name=sheet_name,
                            row_number=sheet_row.row_number,
                            service_name_raw=service,
                            resident_price_raw=resident,
                            nonresident_price_raw=nonresident,
                            currency_raw=_detect_currency(resident, nonresident),
                        )
                    )
            return ParsedWorkbook(rows=tuple(extracted), warnings=tuple(warnings))


@dataclass(frozen=True)
class _DetectedColumns:
    service_index: int | None
    resident_price_index: int | None
    nonresident_price_index: int | None


def _read_shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("main:si", XLSX_NS):
        fragments = [node.text or "" for node in item.findall(".//main:t", XLSX_NS)]
        strings.append("".join(fragments))
    return strings


def _read_sheets(workbook: ZipFile) -> list[tuple[str, str]]:
    workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    rel_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rel_root.findall("pkgrel:Relationship", XLSX_NS)
    }
    sheets: list[tuple[str, str]] = []
    for sheet in workbook_root.findall("main:sheets/main:sheet", XLSX_NS):
        name = sheet.attrib["name"]
        relationship_id = sheet.attrib[f"{{{XLSX_NS['rel']}}}id"]
        target = relationships[relationship_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((name, target))
    return sheets


def _read_sheet_table(
    workbook: ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> list[_SheetRow]:
    root = ElementTree.fromstring(workbook.read(sheet_path))
    hidden_columns = _hidden_column_indexes(root)
    row_values: dict[int, dict[int, str]] = {}
    for row in root.findall(".//main:sheetData/main:row", XLSX_NS):
        if row.attrib.get("hidden") == "1":
            continue
        row_number = int(row.attrib.get("r", len(row_values) + 1))
        values: dict[int, str] = {}
        for cell in row.findall("main:c", XLSX_NS):
            column_index = _column_index(cell.attrib.get("r", "A1"))
            if column_index in hidden_columns:
                continue
            values[column_index] = _cell_text(cell, shared_strings)
        row_values[row_number] = values

    _apply_merged_cells(root, row_values, hidden_columns)
    rows: list[_SheetRow] = []
    for row_number in sorted(row_values):
        values = row_values[row_number]
        width = max(values.keys(), default=-1) + 1
        rows.append(
            _SheetRow(
                row_number=row_number,
                cells=[values.get(index, "") for index in range(width)],
            )
        )
    return rows


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value = cell.find("main:v", XLSX_NS)
    inline = cell.find("main:is/main:t", XLSX_NS)
    if inline is not None:
        return inline.text or ""
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def _column_index(cell_reference: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_reference.upper())
    if letters is None:
        return 0
    result = 0
    for letter in letters.group(1):
        result = result * 26 + (ord(letter) - ord("A") + 1)
    return result - 1


def _row_number(cell_reference: str) -> int:
    digits = re.search(r"(\d+)", cell_reference)
    return int(digits.group(1)) if digits is not None else 1


def _hidden_column_indexes(root: ElementTree.Element) -> set[int]:
    hidden: set[int] = set()
    for column in root.findall("main:cols/main:col", XLSX_NS):
        if column.attrib.get("hidden") != "1":
            continue
        start = int(column.attrib["min"]) - 1
        end = int(column.attrib["max"]) - 1
        hidden.update(range(start, end + 1))
    return hidden


def _apply_merged_cells(
    root: ElementTree.Element,
    row_values: dict[int, dict[int, str]],
    hidden_columns: set[int],
) -> None:
    for merge_cell in root.findall("main:mergeCells/main:mergeCell", XLSX_NS):
        ref = merge_cell.attrib.get("ref", "")
        if ":" not in ref:
            continue
        start_ref, end_ref = ref.split(":", 1)
        start_col = _column_index(start_ref)
        end_col = _column_index(end_ref)
        start_row = _row_number(start_ref)
        end_row = _row_number(end_ref)
        value = row_values.get(start_row, {}).get(start_col, "")
        if not value:
            continue
        for row_number in range(start_row, end_row + 1):
            row = row_values.setdefault(row_number, {})
            for column_index in range(start_col, end_col + 1):
                if column_index not in hidden_columns and column_index not in row:
                    row[column_index] = value


def _detect_header_row(table: list[_SheetRow]) -> int | None:
    for index, row in enumerate(table[:25]):
        normalized = [_normalize_header(cell) for cell in row.cells]
        has_service = any(_looks_like_service_header(cell) for cell in normalized)
        has_price = any(_looks_like_price_header(cell) for cell in normalized)
        if has_service and has_price:
            return index
    return None


def _detect_columns(header: list[str]) -> _DetectedColumns:
    normalized = [_normalize_header(cell) for cell in header]
    service_index = next(
        (index for index, value in enumerate(normalized) if _looks_like_service_header(value)),
        None,
    )
    resident_index = next(
        (
            index
            for index, value in enumerate(normalized)
            if _looks_like_price_header(value)
            and NONRESIDENT_TOKEN not in value
            and "non" not in value
        ),
        None,
    )
    nonresident_index = next(
        (
            index
            for index, value in enumerate(normalized)
            if _looks_like_price_header(value)
            and (NONRESIDENT_TOKEN in value or "non" in value)
        ),
        None,
    )
    return _DetectedColumns(
        service_index=service_index,
        resident_price_index=resident_index,
        nonresident_price_index=nonresident_index,
    )


def _normalize_header(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").split())


def _looks_like_service_header(value: str) -> bool:
    return any(token in value for token in SERVICE_HEADER_TOKENS)


def _looks_like_price_header(value: str) -> bool:
    return any(token in value for token in PRICE_HEADER_TOKENS)


def _cell(row: list[str], index: int) -> str:
    return row[index] if index < len(row) else ""


def _cell_optional(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    value = row[index].strip()
    return value or None


def _detect_currency(*values: str | None) -> str | None:
    text = " ".join(value or "" for value in values).casefold()
    if KZT_SYMBOL in text or "kzt" in text or TENGE_WORD in text:
        return "KZT"
    return None


def parse_kzt_price(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    normalized = (
        raw.replace(KZT_SYMBOL, "")
        .replace("KZT", "")
        .replace("kzt", "")
        .replace(TENGE_WORD, "")
        .replace("\u00a0", " ")
        .strip()
    )
    normalized = normalized.replace(" ", "").replace(",", ".")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None
