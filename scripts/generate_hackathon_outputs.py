from __future__ import annotations

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from medarchive_document_parsers.docx import DocxParser
from medarchive_document_parsers.xlsx import XlsxParser

ARCHIVE_DIR = Path(r"C:\Users\user\Downloads\Telegram Desktop\Хакатон\Хакатон")
OUTPUT_DIR = Path("outputs")
PRICE_RE = re.compile(
    r"(?P<name>[A-Za-zА-Яа-яЁёІіҚқҒғҰұҮүӘәӨөҺһ0-9 .,/()\-]{4,}?)"
    r"\s+(?P<price>\d[\d\s]{2,})(?:\s+(?P<nonresident>\d[\d\s]{2,}))?$"
)


def normalize(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def price(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"[^\d]", "", value)
    return digits


def partner_from_filename(path: Path) -> str:
    stem = path.stem
    return re.sub(r"\s+(прайс|price).*", "", stem, flags=re.IGNORECASE).strip()


def rows_from_pdf(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        import pdfplumber
    except ImportError:
        return [], ["pdfplumber is not installed"]
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                for line_number, line in enumerate(text.splitlines(), start=1):
                    match = PRICE_RE.search(" ".join(line.split()))
                    if not match:
                        continue
                    name = match.group("name").strip(" -.,")
                    if len(name) < 4 or name.isdigit():
                        continue
                    rows.append(
                        {
                            "source_location": f"page {page_index}, line {line_number}",
                            "service_name_raw": name,
                            "price_resident_kzt": price(match.group("price")),
                            "price_nonresident_kzt": price(match.group("nonresident")),
                        }
                    )
    except Exception as exc:
        warnings.append(str(exc))
    return rows[:200], warnings


def rows_from_docx(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    parsed = DocxParser().parse(path.read_bytes())
    return [
        {
            "source_location": f"table {row.table_index}, row {row.row_number}",
            "service_name_raw": row.service_name_raw,
            "price_resident_kzt": price(row.resident_price_raw),
            "price_nonresident_kzt": price(row.nonresident_price_raw),
        }
        for row in parsed.rows
    ], list(parsed.warnings)


def rows_from_xlsx(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    parsed = XlsxParser().parse(path.read_bytes())
    return [
        {
            "source_location": f"{row.sheet_name}!{row.row_number}",
            "service_name_raw": row.service_name_raw,
            "price_resident_kzt": price(row.resident_price_raw),
            "price_nonresident_kzt": price(row.nonresident_price_raw),
        }
        for row in parsed.rows
    ], list(parsed.warnings)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    documents: list[dict[str, object]] = []
    items: list[dict[str, object]] = []
    catalog_by_key: dict[str, dict[str, object]] = {}

    files = sorted(path for path in ARCHIVE_DIR.iterdir() if path.is_file())
    for file_path in files:
        suffix = file_path.suffix.lower()
        status = "processed"
        warnings: list[str] = []
        extracted_rows: list[dict[str, str]] = []
        if suffix == ".docx":
            extracted_rows, warnings = rows_from_docx(file_path)
        elif suffix == ".xlsx":
            extracted_rows, warnings = rows_from_xlsx(file_path)
        elif suffix == ".pdf":
            extracted_rows, warnings = rows_from_pdf(file_path)
        elif suffix == ".xls":
            status = "needs_parser_extra"
            warnings = ["Legacy XLS requires xlrd parser extra in this local environment."]
        else:
            status = "unsupported"
            warnings = [f"Unsupported extension: {suffix}"]

        partner = partner_from_filename(file_path)
        doc_id = str(uuid5(NAMESPACE_URL, f"medarchive:document:{file_path.name}"))
        documents.append(
            {
                "doc_id": doc_id,
                "file_name": file_path.name,
                "file_format": suffix.lstrip(".").upper(),
                "partner_name": partner,
                "parse_status": (
                    status if extracted_rows or status != "processed" else "needs_review"
                ),
                "extracted_rows": len(extracted_rows),
                "warnings": warnings,
            }
        )

        for row_index, row in enumerate(extracted_rows, start=1):
            key = normalize(row["service_name_raw"])
            service_id = str(uuid5(NAMESPACE_URL, f"medarchive:service:{key}"))
            catalog_by_key.setdefault(
                key,
                {
                    "service_id": service_id,
                    "external_service_id": f"svc-{len(catalog_by_key) + 1:04d}",
                    "service_name": row["service_name_raw"],
                    "synonyms": [],
                    "category": "unknown",
                    "is_active": True,
                },
            )
            resident = row["price_resident_kzt"]
            nonresident = row["price_nonresident_kzt"]
            review_reasons: list[str] = []
            if not resident and not nonresident:
                review_reasons.append("missing_price")
            if resident and nonresident and int(nonresident) < int(resident):
                review_reasons.append("nonresident_price_below_resident_price")
            items.append(
                {
                    "item_id": str(
                        uuid5(
                            NAMESPACE_URL,
                            f"medarchive:item:{file_path.name}:{row_index}:{key}",
                        )
                    ),
                    "doc_id": doc_id,
                    "partner_name": partner,
                    "source_file": file_path.name,
                    "source_location": row["source_location"],
                    "service_name_raw": row["service_name_raw"],
                    "service_id": service_id,
                    "price_resident_kzt": resident,
                    "price_nonresident_kzt": nonresident,
                    "is_verified": not review_reasons,
                    "review_reasons": review_reasons,
                }
            )

    catalog = sorted(catalog_by_key.values(), key=lambda item: str(item["service_name"]))
    verified = sum(1 for item in items if item["is_verified"])
    queued = len(items) - verified
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "archive_path": str(ARCHIVE_DIR),
        "document_count": len(documents),
        "format_counts": {
            "pdf": sum(1 for doc in documents if doc["file_format"] == "PDF"),
            "docx": sum(1 for doc in documents if doc["file_format"] == "DOCX"),
            "xlsx": sum(1 for doc in documents if doc["file_format"] == "XLSX"),
            "xls": sum(1 for doc in documents if doc["file_format"] == "XLS"),
        },
        "extracted_item_count": len(items),
        "catalog_service_count": len(catalog),
        "successful_normalization_percent": round((verified / len(items) * 100) if items else 0, 2),
        "review_queue_count": queued,
        "documents": documents,
    }

    (OUTPUT_DIR / "service_catalog_seed.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "processed_database_preview.json").write_text(
        json.dumps({"documents": documents, "price_items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (OUTPUT_DIR / "processed_price_items_preview.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(items[0].keys()) if items else ["item_id"])
        writer.writeheader()
        writer.writerows(items)
    (OUTPUT_DIR / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "quality_report.md").write_text(
        "\n".join(
            [
                "# Отчет качества MedArchive",
                "",
                f"Сформирован: {report['generated_at']}",
                f"Архив: `{ARCHIVE_DIR}`",
                "",
                "## Сводка",
                "",
                f"- Документов: {report['document_count']}",
                f"- Форматы: {report['format_counts']}",
                f"- Извлеченных позиций прайса: {report['extracted_item_count']}",
                f"- Записей в справочнике услуг: {report['catalog_service_count']}",
                f"- Успешная нормализация: {report['successful_normalization_percent']}%",
                f"- Позиции в очереди ручной проверки: {report['review_queue_count']}",
                "",
                "## Примечания",
                "",
                (
                    "- Это preview обработанной базы, сформированный "
                    "из предоставленного архива хакатона."
                ),
                "- Для XLS в текущем локальном окружении нужен optional parser extra `xlrd`.",
                (
                    "- Полный production-прогон нужно запускать через Docker Compose "
                    "с подключенными parser/OCR extras."
                ),
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
