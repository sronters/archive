# Export Contract v1

## Formats

- JSON
- CSV
- XLSX

## Endpoint

```text
GET /api/v1/exports/price-versions
```

Query parameters:

```text
format=json|csv|xlsx
status=published
partner_id=<uuid>
service_id=<uuid>
external_partner_id=<company partner id>
external_service_id=<company service id>
changed_since=<iso-8601 datetime>
limit=1000
offset=0
```

## Required Columns

```text
price_version_id
partner_id
external_partner_id
partner_name
service_id
external_service_id
service_name
resident_price_kzt
nonresident_price_kzt
original_price
original_currency
valid_from
valid_to
published_at
source_document_id
external_source_id
source_file_name
source_sheet
source_page
source_row
```

## Rules

- Exports include both company external IDs and MedArchive internal IDs.
- Exports use the same filters as `GET /api/v1/price-versions`.
- Export rows use deterministic column ordering.
- CSV is UTF-8 with BOM for spreadsheet compatibility.
- XLSX output is a valid Office Open XML workbook.
- Exports must be reproducible and audit-linked.
- Export generation failures must be visible to operators.
