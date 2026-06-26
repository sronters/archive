# Production Test Gates

Every production feature must include the relevant automated gates:

- Unit tests.
- Domain state-machine tests.
- Repository integration tests.
- Migration checks.
- API contract tests.
- Parser golden tests.
- OCR quality tests.
- Matching labeled tests.
- Idempotency tests.
- Worker retry tests.
- Transactional outbox tests.
- Webhook contract tests.
- Frontend workflow tests.
- Load tests.
- Archive security tests.
- Authorization tests.
- Backup and restore test.

## Security

- ZIP Slip and decompression-ratio tests are mandatory for ingestion.
- MIME signature detection must reject extension-only spoofing.
- Authorization tests must cover missing credentials, wrong role, and allowed role.
- Webhooks must be signed and idempotent by event ID.

## Backup And Restore

- Database backup must be restored into an empty environment.
- Object storage backup must restore immutable originals.
- Restore verification must prove price versions, audit events, and provenance links remain queryable.
