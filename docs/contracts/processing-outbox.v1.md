# Processing Outbox Contract v1

## Purpose

Connect ingestion persistence to asynchronous document processing without dispatching queue messages inside the same API transaction.

## Event Type

```text
document.processing_requested
```

## Payload

```json
{
  "document_id": "b58b87f8-1567-4ec7-97f5-7efdb372ea96",
  "batch_id": "38ff93c7-10a4-4949-b78f-6e747a87d901",
  "source_file_id": "771f410d-a294-46c6-a24a-63828692f447",
  "detected_format": "xlsx",
  "storage_key": "originals/upload-1/.../price.xlsx"
}
```

## Rules

- API ingestion writes this event into `outbox_events` in the same transaction as `IngestionBatch`, `SourceFile`, and `PriceDocument`.
- A separate outbox publisher reads unpublished events and dispatches `medarchive.process_document`.
- The current worker implementation supports XLSX, DOCX table processing, and text PDF price-line extraction. It downloads the immutable original from configured storage, creates a durable `ProcessingRun`, persists `ExtractedPriceItem` rows, prepares `ServiceMatch` and `ReviewTask` output, and moves the document through `EXTRACTING` toward `NEEDS_REVIEW` or `VERIFIED`.
- Unsupported formats are marked `PERMANENT_ERROR` until their parser adapters are implemented in later phases.
- Publishing is at-least-once; document processing consumers must be idempotent.
- Publisher failures increment the outbox attempt counter and leave the event unpublished for retry.
