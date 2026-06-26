# Production Quality Bar

## Non-Negotiable Rule

MedArchive must not be evaluated as an MVP. A feature is not done because a happy-path demo works. It is done when it is reliable, observable, testable, secure, auditable, idempotent, and usable by operators on imperfect real documents.

## Matching Quality

Prioritize precision over coverage.

Target:

- automatic service-match precision: at least 98%;
- uncertain matches go to review;
- it is better to auto-match fewer rows with very high precision than publish wrong medical services.

The matcher must preserve:

- candidate list;
- retrieval method;
- retrieval score;
- reranker score;
- matcher version;
- final confidence;
- reason for review when not auto-accepted.

LLM or VLM components cannot invent service IDs or prices. They may assist with ranking or extraction only when the final choice is constrained, verified, and traceable.

## Provenance

For every published value, the system must answer:

- source file;
- source document;
- page, sheet, row, or cell;
- bounding box when available;
- parser name;
- parser version;
- matcher version;
- processing run ID;
- extraction confidence;
- OCR confidence when applicable;
- user or system actor that confirmed it;
- publication timestamp;
- previous price version;
- reason the previous version was superseded.

Operators must see the original document fragment next to extracted values during verification.

## Reliability

Ingestion and processing must be idempotent.

Use:

- SHA-256 identity;
- `partner_id` and effective date when available;
- unique constraints;
- upserts where appropriate;
- idempotency keys;
- transactions;
- processing run version control.

Queue model:

```text
at-least-once delivery + idempotent consumers
```

Worker tasks require:

- retry with exponential backoff;
- maximum attempt count;
- timeout;
- dead-letter queue;
- typed error code;
- manual retry;
- heartbeat for long OCR tasks.

Partial failure behavior:

- if 95 of 100 documents succeed, they continue to completion;
- the batch becomes `completed_with_errors`;
- failed documents remain visible;
- retry can target only failed documents.

Use transactional outbox for DB changes that produce queue or webhook events.

## Security

Required for ingestion:

- safe ZIP extraction;
- ZIP Slip protection;
- ZIP Bomb protection;
- content-based MIME detection;
- file size and page count limits;
- malware scan status;
- immutable original storage;
- access control for documents and review tasks;
- audit trail for human actions;
- no secret leakage in logs;
- strict validation of imports and exports.

Medical and personal data handling must assume sensitive data can appear in documents. Cloud OCR is allowed only if company policy permits it.

## Observability

Every API request, background job, parser run, matcher run, review action, publication action, and export should be traceable.

Required telemetry:

- structured logs;
- metrics;
- traces;
- request and task correlation IDs;
- parser and OCR timing;
- queue depth;
- retry counts;
- failure rate by document type;
- review queue age;
- publication success/failure.

## Testing Requirements

Minimum required tests:

- unit tests for domain services and state transitions;
- integration tests for API, database, storage, and queue adapters;
- parser golden tests for PDF, scanned PDF, XLS/XLSX, DOCX;
- OCR regression tests on real or representative fixtures;
- table extraction tests with bordered and borderless tables;
- matching quality tests with labeled expected services;
- API contract tests against OpenAPI;
- idempotency tests for duplicate upload and worker retry;
- security tests for unsafe ZIPs, bad MIME, oversized files, invalid input;
- backup and restore test;
- export and webhook contract tests.

Golden dataset should include:

- text PDFs;
- scanned PDFs;
- rotated pages;
- Russian, Kazakh, and mixed RU/KZ content;
- tables with and without borders;
- multi-line services;
- resident and nonresident prices;
- one-price documents;
- unusual headers;
- old `.xls` files;
- DOCX with tables and tracked changes.

Quality metrics for extraction:

- service name CER;
- service name exact match;
- price exact match;
- resident/nonresident column accuracy;
- row reconstruction precision and recall;
- table exact-match rate;
- document success rate;
- fallback rate;
- manual-review rate;
- latency p50, p95, p99;
- RAM and CPU usage.

The most important extraction metric is `price_exact_match`; a single digit error can create a commercially wrong record.

## Definition Of Done

A production feature is done only when:

- it handles malformed and partial input;
- errors are visible to operators;
- repeated execution does not duplicate data;
- all persisted results have provenance;
- public API behavior is documented;
- tests cover normal, edge, and failure cases;
- logs, metrics, and traces are usable;
- security constraints are enforced;
- implementation follows ports and adapters where infrastructure can vary;
- documentation explains how to operate and integrate the feature.
