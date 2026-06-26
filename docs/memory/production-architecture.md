# Production Architecture Memory

## Product Definition

MedArchive - не отдельная enterprise-платформа управления медицинскими партнерами. Это интегрируемый сервис автоматической обработки прайс-листов клиник.

Сервис принимает документы разных форматов, извлекает и проверяет услуги и цены, сопоставляет их с корпоративным справочником, предоставляет оператору очередь верификации и передает подтвержденные результаты в существующую информационную систему компании через REST API, webhooks или экспорт.

## Целевая Архитектура

Архитектура: модульный монолит с независимо масштабируемыми worker-процессами.

Пять контуров:

1. Прием и безопасное хранение документов.
2. Надежный асинхронный конвейер извлечения.
3. Нормализация и сопоставление со справочником.
4. Верификация оператором и публикация.
5. Быстрый поиск, API, аудит и аналитика.

Высокоуровневый поток:

```text
Next.js Admin UI
  -> FastAPI /api/v1
  -> PostgreSQL as source of truth
  -> Redis cache and rate limiting
  -> S3/MinIO immutable file storage
  -> RabbitMQ/Celery or Dramatiq workers
  -> extraction, OCR, normalization, validation, publication
```

Workers:

- file inspection worker;
- PDF extraction worker;
- OCR worker;
- XLS/XLSX worker;
- DOCX worker;
- normalization worker;
- validation worker;
- publication worker.

## Processing Pipeline

Ingestion:

- create `IngestionBatch`;
- safely unpack ZIP archives;
- protect against ZIP Slip and ZIP Bomb;
- detect MIME type with libmagic or content-based detection;
- calculate SHA-256;
- record malware scan status;
- save original file in immutable object storage;
- create one logical document record per document;
- enqueue async tasks;
- return `batch_id` immediately with `202 Accepted`.

PDF strategy must be selected per page, not only per file. A single PDF can contain text pages, scanned pages, tables, rotated pages, and multiple price lists.

Canonical extraction model:

```python
class CanonicalDocument:
    document_id: UUID
    pages: list["CanonicalPage"]
    metadata: dict[str, str]
    parser_name: str
    parser_version: str


class CanonicalPage:
    page_number: int
    width: float
    height: float
    blocks: list["TextBlock"]
    tables: list["TableBlock"]


class TextBlock:
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float | None


class TableCell:
    row_index: int
    column_index: int
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float | None
```

Parsers return canonical documents, not final `PriceItem` rows directly. This keeps normalization independent from PDF, DOCX, XLSX, and OCR internals.

## Parser Strategy

Text PDF:

- PyMuPDF for text, coordinates, and pages;
- pdfplumber for tables;
- Camelot/Tabula as fallback if useful;
- custom column detection;
- preserve `page_number` and bbox for extracted values.

Scanned PDF:

- do not depend only on Tesseract;
- benchmark PaddleOCR and Tesseract `rus+kaz+eng` on real documents;
- cloud OCR can be fallback only if company policy allows it;
- pipeline: render page, deskew, orientation detection, denoise, contrast normalization, OCR, table structure detection, column reconstruction, field extraction;
- preserve OCR confidence for every value.

XLS/XLSX:

- process all sheets independently;
- detect header row;
- handle merged cells;
- mark hidden rows and columns;
- do not execute formulas;
- read saved values;
- process legacy `.xls` in a safe worker container.

DOCX:

- `python-docx` alone is not enough for tracked changes;
- inspect OOXML;
- accept `w:ins`;
- exclude `w:del`;
- handle merged cells;
- preserve both text and visual structure when needed.

## Service Matching

Never implement matching as only `cosine_similarity > 0.85 -> accept`. A fixed threshold does not guarantee correctness across embedding models.

Use hybrid matching:

1. Text canonicalization.
2. Exact service name match.
3. Exact synonym match.
4. Source code match.
5. Token/fuzzy match.
6. Semantic candidate retrieval.
7. Candidate reranking.
8. Business-rule filtering.
9. Confidence calibration.
10. Auto-accept or review.

Candidate retrieval can use exact match, synonyms, `pg_trgm`, PostgreSQL FTS, embeddings, category, service code, and neighboring row context.

LLM usage, if added, is allowed only as an auxiliary reranker. It must never invent `service_id`; it may choose only from existing candidates.

## Production Data Model

Core entities:

- `ingestion_batches`: one user upload;
- `source_files`: immutable original files;
- `documents`: logical clinic price documents;
- `processing_runs`: every parser/matcher run with versions and status;
- `extracted_items`: raw extracted rows and fields;
- `match_candidates`: candidate services with retrieval and reranking scores;
- `review_tasks`: human-in-the-loop tasks;
- `price_versions`: immutable price history;
- `audit_events`: actor/system audit trail;
- `exchange_rates`: currency conversion source and rate.

Practical implementation entities:

- `Partner`;
- `Service`;
- `PriceDocument`;
- `ProcessingRun`;
- `ExtractedPriceItem`;
- `ServiceMatch`;
- `ReviewTask`;
- `PriceVersion`;
- `AuditEvent`.

External identifiers are required:

- `Partner.external_id`;
- `Service.external_id`;
- `PriceDocument.external_source_id`.

## Workflow States

Do not model workflow as only `pending`, `processing`, `done`, `error`.

Use explicit states:

```text
UPLOADED
-> INSPECTING
-> READY_FOR_EXTRACTION
-> EXTRACTING
-> EXTRACTED
-> NORMALIZING
-> VALIDATING
-> NEEDS_REVIEW
-> VERIFIED
-> PUBLISHED
```

Error states:

```text
RETRYABLE_ERROR
PERMANENT_ERROR
QUARANTINED
```

All transitions must go through a domain state machine.

## API Production Shape

API must be versioned under `/api/v1`.

Core groups:

- ingestion batches: create, inspect, retry;
- documents: list, inspect, processing runs, reprocess;
- review tasks: list, claim, approve, reject, correct;
- services: list, detail, offers;
- partners: list, detail, prices;
- price changes and exports;
- webhooks and publication status.

OpenAPI documentation is required and must match the implemented API.

## Observability

Every operation must propagate:

- `request_id`;
- `batch_id`;
- `document_id`;
- `processing_run_id`;
- `task_id`.

These IDs must pass through API, queue, workers, logs, metrics, traces, and database records.

Operational dashboards should expose:

- document processing latency;
- OCR latency;
- parser success rate;
- error rate by parser and format;
- auto-match precision;
- manual review volume;
- oldest review task age;
- anomalous price changes;
- active/inactive partners.

## Integration Posture

The company may already have users, clinics, CRM, service catalog, website, database, BI, notifications, logging, and SSO. MedArchive should not duplicate those systems. It should provide adapters.

Integration modes:

- service catalog upload from XLSX/JSON;
- service catalog sync from company API;
- periodic catalog sync;
- pull API for prices and offers;
- webhook after publication;
- CSV/XLSX/JSON/ZIP export;
- local JWT for demo;
- OIDC/API key/OAuth2 client credentials for production;
- MinIO locally, S3 or corporate object storage in production;
- Redis/Celery locally, RabbitMQ/Celery or existing company broker in production.
