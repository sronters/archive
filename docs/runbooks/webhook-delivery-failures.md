# Webhook Delivery Failures

## Signals

- `webhook_deliveries.status` is `retryable` or `dead_letter`.
- `medarchive_webhook_failures_total` increases.
- Integration partner reports missing events.

## Triage

1. Check endpoint URL, event type, event version, and response code.
2. Verify `X-MedArchive-Signature` with the endpoint secret.
3. Confirm idempotency handling by `event_id`.
4. Review retry count and `next_attempt_at`.

## Recovery

- Redeliver from the delivery log after endpoint recovery.
- Rotate endpoint secret if signature verification is compromised.
- Move permanently invalid payloads to dead-letter with an audit note.
