# MedArchive Technical Solution

## 1. Purpose

MedArchive is a production-grade, integration-first service for processing clinic price lists.

It ingests ZIP, PDF, DOCX, XLS, and XLSX files; extracts clinic service names and resident/non-resident prices; normalizes services against the company catalog; routes uncertain records to operators; publishes immutable verified price versions; and exposes the results through REST API, exports, webhooks, and an operational admin UI.

MedArchive is not a CRM, billing system, public marketplace, corporate SSO, or BI platform. It is a replaceable processing component that connects to the company's existing systems.

## 2. Production Principles

Non-negotiable rules:

- no MVP-only shortcuts;
- relational PostgreSQL is the source of truth;
- every extracted and published value needs provenance;
- ingestion, worker processing, publication, and graph projection must be idempotent;
- infrastructure integrations are ports/adapters, not domain dependencies;
- uncertain matching optimizes precision and goes to human review;
- failures must be visible, retryable, auditable, and observable.

## 3. Stack

Default stack:

```text
Backend:        Python 3.12, FastAPI, Pydantic 2
Database:       PostgreSQL 16, SQLAlchemy 2, Alembic
Workers:        Celery with RabbitMQ
Storage:        S3-compatible storage, MinIO locally
Cache:          Redis
Frontend:       Next.js, TypeScript, TanStack Query
Graph:          Apache AGE or postgres_edges read model
Visualization:  Cytoscape.js
Observability:  JSON logs, request IDs, Prometheus metrics, OpenTelemetry-ready structure
Packaging:      Docker Compose, uv, pnpm
```

Local graph backend defaults to `postgres_edges`. Production can use `apache_age` when the PostgreSQL deployment has Apache AGE installed and approved.

## 4. Repository Layout

```text
apps/
  api/        FastAPI API
  worker/     Celery worker entrypoint
  admin-web/  Next.js admin interface
packages/
  domain/              pure domain models, ports, canonical types
  application/         use cases and orchestration
  infrastructure/      SQLAlchemy repositories and external adapters
  document_parsers/    PDF, OCR, DOCX, XLS, XLSX parsers
  matching/            service matching
  shared/              shared support code
migrations/            Alembic migrations
docs/                  contracts, memory, quality gates, runbooks
tests/                 backend and integration tests
```

## 5. Core Domain Model

Primary entities:

```text
Partner
Service
IngestionBatch
SourceFile
PriceDocument
ProcessingRun
ExtractedPriceItem
ServiceMatch
ReviewTask
PriceVersion
AuditEvent
OutboxEvent
WebhookDelivery
GraphNode
GraphEdge
```

Important external identifiers:

```text
partner_id              MedArchive UUID
external_partner_id     company partner ID

service_id              MedArchive UUID
external_service_id     company service catalog ID

source_document_id      MedArchive UUID
external_source_id      source system document/upload ID
```

## 6. Document Workflow

Document states:

```text
UPLOADED
INSPECTING
READY_FOR_EXTRACTION
EXTRACTING
EXTRACTED
MATCHING
VALIDATING
NEEDS_REVIEW
VERIFIED
PUBLISHED
RETRYABLE_ERROR
PERMANENT_ERROR
QUARANTINED
```

The current worker path moves documents through extraction, review preparation, and publication-related states. Direct arbitrary state mutation is not a domain pattern; transitions must be performed by use cases or repositories that understand the workflow.

## 7. Ingestion

The ingestion service supports:

- streamed file handling;
- ZIP and individual files;
- content-based MIME detection;
- SHA-256 identity;
- file-size limits;
- archive file-count limits;
- decompression-ratio checks;
- ZIP Slip prevention;
- immutable storage keys;
- malware scanner port with `not_configured` allowed only for local/dev;
- idempotency-key-aware storage keys;
- partial batch rejection.

The recorder boundary persists:

```text
IngestionBatch
SourceFile
PriceDocument
document.processing_requested OutboxEvent
```

Duplicate handling must be enforced at persistence boundaries using SHA-256, unique constraints, and idempotency keys.

## 8. Extraction Pipeline

All parsers output canonical extracted rows that are persisted as `ExtractedPriceItem`.

Supported parsers:

- XLSX through direct OOXML parsing;
- legacy XLS through `xlrd`;
- DOCX through OOXML table parsing;
- text PDF through PyMuPDF/pdf-style extraction;
- scanned PDF through an OCR adapter boundary.

XLSX parser capabilities:

- all worksheets;
- automatic header-row detection;
- service column detection;
- resident and non-resident price column detection;
- KZT price parsing;
- hidden row awareness;
- hidden column awareness;
- merged-cell propagation;
- sheet and real Excel row-number provenance.

Every processing attempt creates a new `ProcessingRun`. Reprocessing must not overwrite earlier runs.

## 9. Matching

The matching pipeline is deterministic and precision-first.

Current retrieval methods include:

- exact official name;
- exact synonym;
- exact source-code/external ID;
- fuzzy normalized name candidate.

Persisted match data:

```text
candidate service
retrieval method
retrieval score
reranker score
rank
matcher version
```

Auto-acceptance threshold defaults to high precision. Uncertain records create `ReviewTask`.

No model may invent a `service_id`. ML/LLM components, if added later, may only rank or select from existing catalog candidates.

## 10. Human Review

Review tasks are created for:

- unresolved or uncertain service match;
- missing partner;
- empty service name;
- missing or invalid prices;
- non-resident price lower than resident price;
- other validation warnings.

Review APIs:

```text
GET  /api/v1/review-tasks
POST /api/v1/review-tasks/{task_id}/claim
POST /api/v1/review-tasks/{task_id}/approve
POST /api/v1/review-tasks/{task_id}/reject
POST /api/v1/review-tasks/{task_id}/correct
POST /api/v1/review-tasks/{task_id}/release
```

Concurrency rules:

- one active assignee;
- versioned tasks;
- conflict response when task state no longer allows the operation.

Every review decision creates an audit event.

## 11. Price Publication

Verified prices are immutable `PriceVersion` records.

Publication behavior:

- publish new price version;
- close previous current version with `valid_to`;
- mark previous current version as superseded;
- preserve historical versions;
- prevent duplicate publication for the same source document and service;
- emit `price_version.published` through the transactional outbox.

Only `published` prices should appear in integration reads by default.

## 12. Outbox

Outbox events decouple transactional writes from external or derived projections.

Current event examples:

```text
document.processing_requested
price_version.published
```

Projection states:

```text
pending
processing
completed
retrying
dead_letter
```

Retry metadata:

```text
attempts
last_error
next_retry_at
processing_started_at
processed_at
published_at
```

If graph projection or task dispatch fails, the relational write remains intact and the outbox event is retried or dead-lettered according to attempts.

## 13. Graph Read Model

The graph is a derived read model, not a second source of truth.

Backends:

```text
postgres_edges  relational graph edge-table fallback
apache_age      Apache AGE over PostgreSQL
noop            disabled projection
```

Graph nodes:

```text
Partner
Service
RawServiceName
ServiceCategory
PriceDocument
PriceVersion
ReviewDecision
```

Graph edges:

```text
Partner        -[OFFERS]->         Service
RawServiceName -[CONFIRMED_AS]->   Service
RawServiceName -[MATCHED_TO]->     Service
Service        -[BELONGS_TO]->     ServiceCategory
Service        -[HAS_PRICE]->      PriceVersion
PriceVersion   -[EXTRACTED_FROM]-> PriceDocument
PriceVersion   -[SUPERSEDED_BY]->  PriceVersion
```

Graph projection is triggered by outbox after `PriceVersion` publication:

```text
PriceVersion
-> OutboxEvent price_version.published
-> OutboxPublisher
-> GraphProjector
-> GraphRepository
```

Graph rebuild:

```bash
uv run medarchive graph rebuild
```

This clears graph read-model state and replays published price versions from PostgreSQL.

The service-neighborhood API has hard limits:

```text
depth <= 2
nodes <= 200
edges <= 500
```

It returns `truncated=true` when the server cuts the response.

## 14. Admin UI

The admin web app is operational software, not a marketing site.

Implemented workflows include:

- upload documents;
- monitor system status;
- inspect ingestion and processing status;
- review uncertain records;
- see published prices;
- request exports;
- inspect webhook deliveries;
- inspect graph neighborhood through Cytoscape.js.

Graph UI value:

```text
Partner
-> OFFERS
-> Service
-> HAS_PRICE
-> PriceVersion
-> EXTRACTED_FROM
-> PriceDocument
```

The UI should not render thousands of nodes. It starts with a bounded neighborhood and expands only by explicit operator action.

## 15. API Surface

Namespace:

```text
/api/v1
```

Important endpoints:

```text
POST /api/v1/ingestion-batches
GET  /api/v1/review-tasks
POST /api/v1/review-tasks/{task_id}/claim
POST /api/v1/review-tasks/{task_id}/approve
POST /api/v1/review-tasks/{task_id}/reject
POST /api/v1/review-tasks/{task_id}/correct
GET  /api/v1/price-versions
GET  /api/v1/services/{external_service_id}/offers
GET  /api/v1/partners/{external_partner_id}/prices
GET  /api/v1/price-changes
GET  /api/v1/exports/price-versions
GET  /api/v1/evidence/extracted-items/{extracted_item_id}
GET  /api/v1/services/search
GET  /api/v1/partners/search
GET  /api/v1/graph/services/{service_id}/neighborhood
GET  /api/v1/system/status
GET  /api/v1/metrics
```

OpenAPI is generated by FastAPI at:

```text
/openapi.json
```

## 16. Integration Contracts

Contracts live in:

```text
docs/contracts/
```

Current contracts:

- authentication context;
- document ingestion;
- exports;
- graph read model;
- partner sync;
- price publication;
- processing outbox;
- review tasks;
- service catalog sync;
- webhook events.

Company-specific API logic must stay outside domain/application logic and behind adapters.

## 17. Authentication And Authorization

Default local mode:

```text
API keys / local auth headers
```

Production modes:

```text
OIDC
OAuth2 client credentials
API key
trusted reverse-proxy identity
```

Roles:

```text
viewer
operator
senior_operator
catalog_manager
administrator
auditor
integration_client
```

Authorization must be enforced in backend APIs, not only hidden in the UI.

## 18. Observability

Implemented and expected observability:

- request ID middleware;
- system status endpoint;
- Prometheus-style metrics endpoint;
- structured operational events;
- outbox attempts and last errors;
- webhook delivery logs;
- parser names and versions;
- processing run IDs;
- graph projection status.

Metrics should cover:

```text
documents received
documents completed
documents failed
processing duration
queue age
retry count
review queue size
review task age
automatic match coverage
automatic match correction rate
webhook failures
API latency
```

## 19. Quality And Tests

Current test suite covers:

- API health and readiness;
- auth and RBAC;
- ingestion security checks;
- document processing;
- XLSX vertical slice;
- real multi-sheet XLSX to graph projection vertical slice;
- DOCX parser;
- text PDF parser;
- OCR adapter;
- review preparation;
- review task operations;
- immutable price publication;
- exports;
- webhooks;
- search;
- evidence;
- graph API and projection;
- graph rebuild behavior;
- quality documentation.

The connected real XLSX graph test is:

```text
tests/test_real_xlsx_graph_vertical_slice.py
```

It verifies:

- large workbook ingestion;
- duplicate upload does not create a second document;
- all sheets are analyzed;
- hidden rows do not become extracted prices;
- sheet and row provenance exists for every item;
- uncertain service creates review;
- correction creates one price version;
- repeated correction does not create a second price version;
- outbox publishes graph projection;
- graph neighborhood contains Partner, Service, PriceVersion, and PriceDocument.

## 20. Deployment Model

Local:

```text
Docker Compose
PostgreSQL
RabbitMQ
Redis
MinIO
api
worker
frontend
```

Production:

- use company-approved PostgreSQL;
- enable Apache AGE only when approved and available;
- configure RabbitMQ or company broker;
- configure object storage adapter;
- configure malware scanner;
- configure OCR provider only if policy allows;
- configure OIDC/OAuth2/API-key modes;
- configure webhook targets and signing secrets.

## 21. Remaining Production Work

The repository now has the architecture and a connected XLSX-to-graph proof through real application services. Remaining production work depends on company inputs:

- real partner source API;
- real service catalog source API;
- real sample price lists;
- SSO metadata;
- webhook receiver URLs;
- OCR provider policy and credentials;
- retention and audit policy;
- production infrastructure sizing.

Engineering next steps:

- run the vertical slice against a real company XLSX;
- add PostgreSQL-backed integration tests in CI;
- add parser golden files for RU/KZ clinic-specific layouts;
- harden partner/date resolution from document metadata;
- expand review UI evidence panel for source fragments;
- measure matching precision on labeled data.
