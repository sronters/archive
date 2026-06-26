# Review Tasks Contract v1

## Purpose

Expose human review work created from extracted price rows that cannot be safely auto-accepted.

## Endpoints

```text
GET  /api/v1/review-tasks
POST /api/v1/review-tasks/{task_id}/claim
POST /api/v1/review-tasks/{task_id}/approve
POST /api/v1/review-tasks/{task_id}/reject
POST /api/v1/review-tasks/{task_id}/correct
POST /api/v1/review-tasks/{task_id}/release
```

## List Query

```text
status=open
limit=50
offset=0
```

Rules:

- `limit` is bounded to `1..200`.
- `offset` must be non-negative.
- Default list scope is open tasks.
- Results are ordered by priority descending and creation time ascending.

## Task Shape

```json
{
  "task_id": "3810d2be-6ccd-472a-840e-4830ae0b4673",
  "extracted_item_id": "76ad441c-cc76-4f46-9028-25e81d2372d0",
  "reason": "service_match_uncertain;partner_unresolved",
  "priority": 80,
  "status": "open",
  "assigned_to": null,
  "version": 0
}
```

## Claim Request

```json
{
  "operator_id": "94413528-e548-4098-8588-b3c4f51a0996"
}
```

Rules:

- A task may be claimed only from `open` or already `claimed` by the same operator.
- Claiming sets `status=claimed`, stores `assigned_to`, and increments `version`.
- If another operator already owns the task, the API returns `409 Conflict`.
- If the task does not exist, the API returns `404 Not Found`.
- Future identity integration must derive `operator_id` from the configured identity adapter rather than trusting UI-local assumptions.

## Decision Requests

Approve uses the highest-ranked persisted service match and parsed extracted prices:

```json
{
  "operator_id": "94413528-e548-4098-8588-b3c4f51a0996"
}
```

Reject requires a business reason:

```json
{
  "operator_id": "94413528-e548-4098-8588-b3c4f51a0996",
  "reason": "Row is not a billable medical service."
}
```

Correct publishes operator-provided service and price values:

```json
{
  "operator_id": "94413528-e548-4098-8588-b3c4f51a0996",
  "service_id": "02eef18e-3684-4d2d-a789-ed7c05818178",
  "resident_price_kzt": "25000",
  "nonresident_price_kzt": "32000"
}
```

Release uses the same body as claim.

Decision response:

```json
{
  "task": {
    "task_id": "3810d2be-6ccd-472a-840e-4830ae0b4673",
    "extracted_item_id": "76ad441c-cc76-4f46-9028-25e81d2372d0",
    "reason": "service_match_uncertain;partner_unresolved",
    "priority": 80,
    "status": "approved",
    "assigned_to": "94413528-e548-4098-8588-b3c4f51a0996",
    "version": 2
  },
  "price_version_id": "6c591fed-a52c-4b07-a905-954d00f7d772",
  "audit_event_id": "22e79d8d-6685-46e9-850d-6cfda9b382bd"
}
```

Rules:

- Approve and correct publish immutable `PriceVersion` records.
- Reject and release do not publish price versions.
- Every decision creates an `AuditEvent`.
- Decisions are allowed only from `open` or `claimed`, and a task claimed by another operator returns `409 Conflict`.
- Correct requires at least one numeric price value.
- Approve requires a resolved partner, at least one numeric extracted price, and an existing service match.

## Review Preparation

Worker-side XLSX processing prepares review output after extraction:

- loads active services from the catalog table;
- persists all deterministic match candidates in `service_matches`;
- creates `review_tasks` for invalid or uncertain rows;
- marks documents `NEEDS_REVIEW` when review work exists;
- marks documents `VERIFIED` only when every extracted row passes validation and precise matching.
