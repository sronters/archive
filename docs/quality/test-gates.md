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

## Connected XLSX Vertical Slice

The XLSX processing milestone is not complete unless one automated test proves:

- a multi-sheet XLSX is accepted through ingestion;
- duplicate upload does not create a second document;
- hidden rows and hidden columns do not produce false prices;
- merged cells do not break header detection;
- every extracted row has sheet and row provenance;
- uncertain rows create review tasks;
- operator correction creates exactly one immutable price version;
- repeated correction does not create a duplicate price version;
- `price_version.published` is projected through outbox;
- graph neighborhood exposes `Partner -> Service -> PriceVersion -> PriceDocument`.

## Backup And Restore

- Database backup must be restored into an empty environment.
- Object storage backup must restore immutable originals.
- Restore verification must prove price versions, audit events, and provenance links remain queryable.
