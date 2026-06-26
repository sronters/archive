# Service Catalog Synchronization Contract v1

## Purpose

Synchronize the company service catalog for matching extracted price-list rows.

## Modes

- `file`: XLSX or JSON upload.
- `remote_api`: company API pull.
- `scheduled_sync`: periodic company API synchronization.

## Payload

```json
{
  "schema_version": "1.0",
  "external_service_id": "svc-000123",
  "official_name": "МРТ головного мозга",
  "synonyms": ["Магнитно-резонансная томография головного мозга"],
  "category": "diagnostics",
  "is_active": true,
  "updated_at": "2026-06-26T00:00:00Z"
}
```

## Rules

- `external_service_id` is preserved in every published result.
- Catalog imports are versioned and auditable.
- Duplicate detection must be reported before import finalization.
- Deactivation must not delete historical price versions.

## File Import API

```text
POST /api/v1/service-catalog/imports
```

Form fields:

```text
file=<json file>
mode=preview|apply
actor_id=<optional operator uuid>
```

Rules:

- `preview` validates and reports create/update/deactivation counts without writing rows.
- `apply` is rejected at the service layer when validation issues exist.
- Duplicate `external_service_id` values are reported as issues.
- JSON may be either a list of catalog rows or an object with an `items` list.
- Applied imports upsert `services` by `external_service_id`.
- Applied imports write audit events for changed service rows.
