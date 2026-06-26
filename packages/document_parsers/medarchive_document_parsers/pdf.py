from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Any, cast

KZT_SYMBOL = "\u20b8"
TENGE_WORD = "\u0442\u0435\u043d\u0433\u0435"


@dataclass(frozen=True)
class ExtractedPdfPriceRow:
    page_number: int
    line_number: int
    bbox: tuple[float, float, float, float] | None
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedPdfDocument:
    rows: tuple[ExtractedPdfPriceRow, ...]
    warnings: tuple[str, ...] = ()


class PdfTextParser:
    parser_name = "pdf-pymupdf-text"
    parser_version = "0.1.0"

    def parse(self, content: bytes) -> ParsedPdfDocument:
        fitz = importlib.import_module("fitz")
        document = fitz.open(stream=content, filetype="pdf")
        extracted: list[ExtractedPdfPriceRow] = []
        warnings: list[str] = []
        try:
            for page_index, page in enumerate(document, start=1):
                page_rows = _page_rows(page, page_number=page_index)
                if not page_rows:
                    warnings.append(f"page {page_index}: no price rows detected")
                extracted.extend(page_rows)
        finally:
            document.close()
        return ParsedPdfDocument(rows=tuple(extracted), warnings=tuple(warnings))


def _page_rows(page: Any, *, page_number: int) -> list[ExtractedPdfPriceRow]:
    blocks = cast(list[tuple[float, float, float, float, str, int, int]], page.get_text("blocks"))
    ordered_blocks = sorted(blocks, key=lambda block: (block[1], block[0]))
    rows: list[ExtractedPdfPriceRow] = []
    line_number = 0
    for block in ordered_blocks:
        x0, y0, x1, y1, text, _block_no, _block_type = block
        for line in text.splitlines():
            line_number += 1
            parsed = _parse_price_line(line)
            if parsed is None:
                continue
            service, resident, nonresident = parsed
            rows.append(
                ExtractedPdfPriceRow(
                    page_number=page_number,
                    line_number=line_number,
                    bbox=(float(x0), float(y0), float(x1), float(y1)),
                    service_name_raw=service,
                    resident_price_raw=resident,
                    nonresident_price_raw=nonresident,
                    currency_raw=_detect_currency(line),
                )
            )
    return rows


def _parse_price_line(line: str) -> tuple[str, str, str | None] | None:
    cleaned = " ".join(line.strip().split())
    if not cleaned or _looks_like_header(cleaned):
        return None
    match = re.match(
        r"^(?P<service>.+?)\s+(?P<resident>\d[\d,.]*)"
        r"(?:\s+(?P<nonresident>\d[\d,.]*))?$",
        cleaned,
    )
    if match is None:
        return None
    service = match.group("service").strip()
    resident = match.group("resident").strip()
    nonresident = match.group("nonresident")
    if not service:
        return None
    return service, resident, nonresident.strip() if nonresident else None


def _looks_like_header(value: str) -> bool:
    normalized = value.casefold()
    return ("service" in normalized or "\u0443\u0441\u043b\u0443\u0433" in normalized) and (
        "price" in normalized
        or "\u0446\u0435\u043d" in normalized
        or "kzt" in normalized
    )


def _detect_currency(value: str) -> str | None:
    text = value.casefold()
    if KZT_SYMBOL in text or "kzt" in text or TENGE_WORD in text:
        return "KZT"
    return None
