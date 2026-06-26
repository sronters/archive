# Document Ingestion Contract v1

## Endpoint

```text
POST /api/v1/ingestion-batches
```

## Response

```json
{
  "batch_id": "4fddc245-6f20-4bb0-8aa8-2efdb601d55e",
  "status": "accepted",
  "accepted_documents_count": 12,
  "rejected_documents_count": 1,
  "links": {
    "self": "/api/v1/ingestion-batches/4fddc245-6f20-4bb0-8aa8-2efdb601d55e",
    "documents": "/api/v1/documents?batch_id=4fddc245-6f20-4bb0-8aa8-2efdb601d55e"
  }
}
```

## Rules

- The API returns `202 Accepted`; it must not wait for parsing or OCR.
- Uploads are passed from FastAPI to the application layer as streams; the route must not read complete upload bodies into memory.
- Non-seekable upload streams are safely spooled before MIME inspection, SHA-256 calculation, malware scanning, and immutable storage.
- ZIP Slip, ZIP Bomb, file count, and decompression ratio protections are required.
- SHA-256 is calculated for every source file.
- Originals are stored immutably.
- Duplicate upload detection uses SHA-256 plus business context when available.
