from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

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
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(frozen=True)
class ExtractedDocxPriceRow:
    table_index: int
    row_number: int
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedDocxDocument:
    rows: tuple[ExtractedDocxPriceRow, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DetectedColumns:
    service_index: int | None
    resident_price_index: int | None
    nonresident_price_index: int | None


class DocxParser:
    parser_name = "docx-ooxml-stdlib"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedDocxDocument:
        try:
            with ZipFile(BytesIO(content)) as document:
                xml = document.read("word/document.xml")
        except (BadZipFile, KeyError) as exc:
            raise ValueError("DOCX cannot be opened or has no word/document.xml.") from exc

        root = ElementTree.fromstring(xml)
        extracted: list[ExtractedDocxPriceRow] = []
        warnings: list[str] = []
        for table_index, table in enumerate(root.findall(".//w:tbl", WORD_NS), start=1):
            rows = _table_rows(table)
            header_index = _detect_header_row(rows)
            if header_index is None:
                warnings.append(f"table {table_index}: header row not detected")
                continue
            columns = _detect_columns(rows[header_index])
            if columns.service_index is None:
                warnings.append(f"table {table_index}: service column not detected")
                continue
            for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
                service = _cell(row, columns.service_index).strip()
                if not service:
                    continue
                resident = _cell_optional(row, columns.resident_price_index)
                nonresident = _cell_optional(row, columns.nonresident_price_index)
                if resident is None and nonresident is None:
                    continue
                extracted.append(
                    ExtractedDocxPriceRow(
                        table_index=table_index,
                        row_number=row_number,
                        service_name_raw=service,
                        resident_price_raw=resident,
                        nonresident_price_raw=nonresident,
                        currency_raw=_detect_currency(resident, nonresident),
                    )
                )
        return ParsedDocxDocument(rows=tuple(extracted), warnings=tuple(warnings))


def _table_rows(table: ElementTree.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("w:tr", WORD_NS):
        cells: list[str] = []
        for cell in row.findall("w:tc", WORD_NS):
            text = " ".join(
                node.text or ""
                for node in cell.findall(".//w:t", WORD_NS)
            )
            span = _grid_span(cell)
            cells.extend([_normalize_cell_text(text)] * span)
        rows.append(cells)
    return rows


def _grid_span(cell: ElementTree.Element) -> int:
    grid_span = cell.find("w:tcPr/w:gridSpan", WORD_NS)
    if grid_span is None:
        return 1
    value = grid_span.attrib.get(f"{{{WORD_NS['w']}}}val")
    if value is None:
        return 1
    try:
        return max(int(value), 1)
    except ValueError:
        return 1


def _detect_header_row(table: list[list[str]]) -> int | None:
    for index, row in enumerate(table[:25]):
        normalized = [_normalize_header(cell) for cell in row]
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


def _normalize_cell_text(value: str) -> str:
    return " ".join(value.split())


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
