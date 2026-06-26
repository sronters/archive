# MedArchive

MedArchive is an integration-first, production-grade service for processing clinic price lists.

It is designed to accept ZIP, PDF, DOCX, XLS, and XLSX files; extract partner, service, resident price, and non-resident price data; normalize services against a company catalog; route uncertain records to human review; preserve provenance and immutable price history; and deliver verified results through REST API, webhooks, and exports.

This repository is not an MVP scaffold. Every implementation must preserve production constraints from [AGENTS.md](AGENTS.md) and the memory documents in [docs/memory](docs/memory).

MedArchive's product difference is evidence-first publication: it proves where every price came from, learns repeated partner formats only after operator confirmation, detects its own uncertainty, and publishes integration-ready price versions instead of just showing an extracted table.

The unified technical description is maintained in [docs/technical-solution.md](docs/technical-solution.md).

## Architecture

```text
apps/
  api/        FastAPI application
  worker/     Celery worker entrypoint
  admin-web/  Next.js operational admin UI
packages/
  domain/              Pure domain entities, workflow, errors, canonical models, ports
  application/         Use cases and orchestration services
  infrastructure/      SQLAlchemy, storage, queue, auth, external adapters
  document_parsers/    Parser adapters that output canonical documents
  matching/            Service matching pipeline
  shared/              Cross-cutting shared utilities
migrations/            Alembic migrations
tests/                 Backend tests
infrastructure/        Operational config and deployment assets
docs/                  Contracts, runbooks, memory
```

## Local Development

Target runtime:

- Python 3.12
- Node.js 24+
- pnpm 10+
- uv
- Docker and Docker Compose

Start dependencies and apps:

```bash
make up
```

Run backend checks:

```bash
make backend-check
```

Run frontend checks:

```bash
make frontend-check
```

Run all checks:

```bash
make check
```

## API

The API namespace is `/api/v1`.

Initial operational endpoints:

- `GET /health`
- `GET /ready`
- `GET /api/v1/system/status`
- `POST /api/v1/ingestion-batches`
- `POST /api/v1/service-catalog/imports`
- `POST /api/v1/partners/imports`
- `GET /api/v1/review-tasks`
- `POST /api/v1/review-tasks/{task_id}/claim`
- `POST /api/v1/review-tasks/{task_id}/approve`
- `POST /api/v1/review-tasks/{task_id}/reject`
- `POST /api/v1/review-tasks/{task_id}/correct`
- `POST /api/v1/review-tasks/{task_id}/release`
- `GET /api/v1/price-versions`
- `GET /api/v1/services/{external_service_id}/offers`
- `GET /api/v1/partners/{external_partner_id}/prices`
- `GET /api/v1/price-changes`
- `GET /api/v1/exports/price-versions`
- `GET /api/v1/evidence/extracted-items/{extracted_item_id}`
- `GET /api/v1/services/search`
- `GET /api/v1/partners/search`
- `GET /api/v1/graph/services/{service_id}/neighborhood`

The OpenAPI document is exposed by FastAPI at `/openapi.json`.

## Current Implementation Stage

Implemented foundation:

- Integration contract documentation.
- Monorepo structure.
- FastAPI application factory and health/readiness endpoints.
- Domain entities, workflow states, typed error codes, canonical document model, and infrastructure ports.
- SQLAlchemy metadata for core entities.
- Alembic baseline migration.
- Celery worker entrypoint.
- Next.js admin shell.
- CI workflow definition.
- Initial backend tests for workflow and API health.
- `POST /api/v1/ingestion-batches` facade with `202 Accepted`, streamed upload handling, upload limits, MIME sniffing, safe ZIP checks, local immutable storage adapter, idempotency-key-aware storage keys, and malware scanner port status.
- Ingestion recorder boundary with SQLAlchemy implementation that writes `IngestionBatch`, `SourceFile`, `PriceDocument`, and `document.processing_requested` outbox events.
- XLSX vertical-slice application service with all-sheet parsing, header detection, service/price column detection, row provenance, KZT price parsing, deterministic matching, validation reasons, and review routing.
- Real XLSX graph vertical-slice test that processes a large multi-sheet workbook through ingestion, immutable storage, document processing, review correction, immutable `PriceVersion`, outbox graph projection, and service-neighborhood visualization contract.
- XLSX parser hardening for hidden rows, hidden columns, merged cells, multiple sheets, and real Excel row-number provenance.
- Outbox publisher that dispatches `document.processing_requested` events to Celery and marks events published after successful dispatch.
- Worker-side XLSX document processing service that downloads immutable originals, creates durable `ProcessingRun` records, persists `ExtractedPriceItem` rows, and moves documents through `EXTRACTING` to `EXTRACTED`.
- DOCX OOXML table parser and worker integration for direct DOCX extraction into the same durable `ProcessingRun` and `ExtractedPriceItem` pipeline.
- Text PDF parser based on PyMuPDF with page, line, and bounding-box provenance, wired into the same durable processing and review pipeline.
- Worker-side review preparation that persists deterministic `ServiceMatch` candidates, creates `ReviewTask` rows for uncertain or invalid extracted items, and marks documents `NEEDS_REVIEW` or `VERIFIED`.
- Initial review queue API with list and claim operations, bounded pagination, one-assignee conflict behavior, and typed response contracts.
- Review decision API for approve, reject, correct, and release operations.
- Transactional audit events for every review decision.
- Immutable `PriceVersion` publication from approve/correct decisions, with previous current prices superseded and duplicate publication guarded by source document plus service.
- Deterministic matcher source-code exact matching in addition to official-name, synonym, and fuzzy candidates.
- Published price-version read API with status, partner, service, changed-since, limit, and offset filters.
- Integration read aliases for service offers, partner prices, and changed-since price polling.
- JSON, CSV, and XLSX exports for published price versions with internal and external IDs preserved.
- Service catalog JSON import with preview/apply modes, duplicate external ID validation, upsert by `external_service_id`, deactivation support, and audit events.
- Partner JSON import with preview/apply modes, duplicate external ID validation, upsert by `external_partner_id`, deactivation support, and audit events.
- Backend-enforced local API-key authentication and RBAC for ingestion, catalog imports, review operations, integration reads, and exports.
- Legacy `.xls` worker support through a dedicated parser adapter using `xlrd`.
- OCR scanned-PDF parser adapter boundary with configurable OCR engine, row provenance, confidence warnings, and not-configured failure behavior.
- Remote API catalog synchronization service, HTTP JSON client, scheduled sync runner, and Celery task hook.
- Signed webhook delivery service with retry/dead-letter status and durable `webhook_deliveries` migration.
- Operational admin console covering upload, status, review, processing runs, published prices, exports, webhook deliveries, and system status.
- Request ID middleware and Prometheus-style `/api/v1/metrics` endpoint.
- Runbooks, golden dataset manifest, and security/load/backup quality gate documentation covered by tests.
- Service and partner search APIs with query, category/city, active-state, limit, and offset filters.
- OIDC/OAuth2-compatible Bearer-token adapter and trusted reverse-proxy identity adapter.
- Concrete HTTP OCR engine adapter with PDF page rendering, signed deployment token support, response validation, and worker fallback for scanned PDFs.
- Admin UI API workflows for refresh, ingestion upload, and export using configured identity headers.
- Runtime HTTP request counters and duration histogram metrics.
- Evidence API for extracted prices, including source file, SHA-256, parser, parser version, processing run, page/sheet/row, bbox, raw values, confidence, and raw parser payload.
- Confirmed partner profile model for manually approved clinic layouts and normalization rules.
- Price diff service that classifies new, removed, changed, unchanged, and anomalous service prices.
- GraphRepository abstraction with `postgres_edges`, `apache_age`, and `noop` backends.
- Outbox-driven graph projection for `price_version.published` events.
- Graph read API for service neighborhoods and Cytoscape.js visualization in the admin UI.
- Rebuildable graph read model with `uv run medarchive graph rebuild`, retry/dead-letter projection state, hard neighborhood limits, and `SUPERSEDED_BY` price-version history.

Deployment-specific work remains outside the repository until the company provides real endpoints, secrets, data retention policy, OCR provider credentials, SSO metadata, webhook receiver URLs, and production infrastructure values.

Those phases must be implemented in order and must not be represented as production-complete until their tests and acceptance gates exist.
