# Webhook Events Contract v1

## Events

```text
price_list.processing_completed
price_list.needs_review
price_list.published
price_list.failed
price_version.created
```

## Envelope

```json
{
  "schema_version": "1.0",
  "event_id": "018fcdf0-3f55-7be9-9604-aedbdb188c5b",
  "event_type": "price_list.published",
  "occurred_at": "2026-06-26T10:15:30Z",
  "payload": {},
  "signature": "sha256=..."
}
```

## Rules

- Payloads are signed.
- Delivery is retried with exponential backoff.
- Delivery attempts are logged.
- Event IDs are idempotency keys for receivers.
- Failed deliveries enter a dead-letter state and support manual redelivery.
