# Verified Price Publication Contract v1

## Purpose

Publish verified prices as immutable price versions.

## Payload

```json
{
  "schema_version": "1.0",
  "price_version_id": "722b8e2b-5d43-4dc1-ae7a-0291373fb6d3",
  "partner_id": "902be937-5013-42af-a81d-164ddcc53144",
  "external_partner_id": "clinic-001754",
  "service_id": "ddc3ce75-d2e4-4bb1-8f14-c5be7f76b2be",
  "external_service_id": "svc-000123",
  "resident_price_kzt": "25000.00",
  "nonresident_price_kzt": "32000.00",
  "valid_from": "2026-06-25",
  "published_at": "2026-06-26T10:15:30Z",
  "source_document_id": "9ab0efdd-82a6-434b-91bb-dfb09b3ab9d0",
  "external_source_id": "company-upload-789"
}
```

## Rules

- Repeated publication of the same verified decision must be idempotent.
- Previous current versions are closed with `valid_to`; they are never deleted.
- Only `published` records appear in integration read APIs by default.
- Current implementation publishes from review approve/correct decisions.
- A repeated approve/correct for the same source document and service returns the existing published version instead of creating a duplicate.
- Publishing requires a resolved partner, selected service, effective date or fallback publication date, and at least one numeric KZT price.
- Review publication writes an audit event in the same transaction as the review task state change.

## Read API

```text
GET /api/v1/price-versions
GET /api/v1/services/{external_service_id}/offers
GET /api/v1/partners/{external_partner_id}/prices
GET /api/v1/price-changes
```

Query parameters:

```text
status=published
partner_id=<uuid>
service_id=<uuid>
changed_since=<iso-8601 datetime>
limit=50
offset=0
```

Rules:

- `status=published` is the default so integration callers do not accidentally consume drafts or rejected records.
- Responses include both MedArchive internal UUIDs and company external IDs when available.
- Pagination is bounded to `1..200` rows per request.
- `changed_since` filters on `PriceVersion.updated_at` for integration polling.
- Service offers filter by `external_service_id` and published status.
- Partner prices filter by `external_partner_id` and published status.
- Price changes require a `changed_since` cursor and return published rows changed after that timestamp.
