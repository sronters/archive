# Partner Synchronization Contract v1

## Purpose

Synchronize company partner records into MedArchive without making MedArchive the source of truth for partners.

## Payload

```json
{
  "schema_version": "1.0",
  "external_partner_id": "clinic-001754",
  "name": "Medical Center",
  "bin": "123456789012",
  "city": "Astana",
  "is_active": true,
  "updated_at": "2026-06-26T00:00:00Z"
}
```

## Rules

- `external_partner_id` is the stable company identifier.
- MedArchive creates or updates its internal `partner_id`.
- Deactivation is represented by `is_active=false`, not destructive deletion.
- Filename-based partner guessing may only produce suggestions, never silent partner creation.

## File Import API

```text
POST /api/v1/partners/imports
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
- Duplicate `external_partner_id` values are reported as issues.
- JSON may be either a list of partner rows or an object with an `items` list.
- Applied imports upsert `partners` by `external_partner_id`.
- Applied imports write audit events for changed partner rows.
