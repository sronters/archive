# Golden Dataset Manifest

The golden dataset must be versioned outside source control when files contain real clinic data. This manifest defines required fixture classes and acceptance metrics.

## Required Fixture Classes

- Text PDF with selectable text and tables.
- Scanned PDF with Cyrillic service names.
- Mixed PDF containing text pages and scanned pages.
- XLS legacy workbook.
- XLSX workbook with multiple sheets, merged cells, hidden rows, and hidden columns.
- DOCX table document.
- DOCX document with tracked changes rendered as final text.
- RU, KZ, and mixed RU/KZ documents.
- Bordered and borderless tables.
- Rotated and low-quality scans.
- Duplicate uploads.
- Malformed ZIP files.
- Oversized archives.
- Unsupported files.

## Required Metrics

- `service_name_exact_match`
- `service_name_character_error_rate`
- `price_exact_match`
- `resident_nonresident_column_accuracy`
- `row_reconstruction_precision`
- `row_reconstruction_recall`
- `document_success_rate`
- `manual_review_rate`
- `processing_p50_ms`
- `processing_p95_ms`
- `processing_p99_ms`

`price_exact_match` is the primary OCR correctness metric.
