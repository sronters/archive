# Failed Document Processing

## Signals

- `price_documents.status` is `RETRYABLE_ERROR` or `PERMANENT_ERROR`.
- `processing_runs.error_code` or worker logs contain parser, OCR, catalog, or storage errors.
- `medarchive_documents_failed` increases.

## Triage

1. Find the `document_id`, `processing_run_id`, `source_file.sha256`, and parser version.
2. Confirm the original object exists in immutable storage.
3. Check malware scan status before downloading or reprocessing.
4. Inspect parser warnings and extracted row count.
5. For OCR failures, verify page renderability, language pack availability, and confidence output.

## Recovery

- Retry only retryable errors after dependency recovery.
- Reprocess by creating a new `ProcessingRun`; never overwrite previous extracted rows.
- For permanent parser errors, route the source to manual review or supplier correction.

## Audit

Record the operator, reason, old status, new status, and linked run ID.
