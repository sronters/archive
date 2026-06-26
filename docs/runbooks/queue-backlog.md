# Queue Backlog

## Signals

- Queue age grows beyond SLA.
- Celery workers are unavailable or saturated.
- Documents remain `READY_FOR_EXTRACTION` or `EXTRACTING`.

## Triage

1. Check RabbitMQ health and queue depth.
2. Check worker process count and task error rate.
3. Compare OCR duration against document volume.
4. Verify object storage and database readiness.

## Recovery

- Scale workers for parser/OCR load.
- Pause ingestion if queue age threatens retention or review SLA.
- Re-run failed jobs only after the dependency failure is understood.
