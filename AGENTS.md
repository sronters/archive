# MedArchive Agent Memory

## Главный принцип

MedArchive не является MVP, демо-скриптом или хакатонной заглушкой. Любой код, документация, архитектурное решение и UI должны проектироваться как production-level компонент, который реальная компания сможет развернуть, поддерживать, масштабировать и подключить к существующим системам.

Запрещено снижать планку до "достаточно для демо", если это ломает надежность, сопровождаемость, аудит, безопасность, тестируемость или интеграционную пригодность.

## Что мы строим

MedArchive - интегрируемый сервис автоматической обработки прайс-листов клиник. Он принимает документы разных форматов, извлекает и проверяет услуги и цены, сопоставляет их с корпоративным справочником, предоставляет оператору очередь верификации и передает подтвержденные результаты в существующую информационную систему компании через REST API, webhooks или экспорт.

Продукт должен быть:

- полностью рабочим сам по себе для демонстрации;
- готовым к production-развертыванию;
- легко интегрируемым в текущий контур компании;
- надежным при повторной обработке, сбоях очередей и частичных ошибках;
- maintainable, scalable, observable, testable.

## Архитектурная позиция

Предпочтительная архитектура - модульный монолит с четкими доменными границами и независимо масштабируемыми worker-процессами. Не создавать десятки микросервисов без реальной причины.

Основные контуры:

- прием и безопасное хранение документов;
- асинхронный конвейер извлечения;
- нормализация и сопоставление со справочником;
- ручная верификация и публикация;
- быстрый поиск, API, аудит и аналитика качества.

## Preferred Production Stack

- Backend: Python 3.12, FastAPI, Pydantic 2.
- ORM and migrations: SQLAlchemy 2, Alembic.
- Database: PostgreSQL 16.
- Search: PostgreSQL FTS, `pg_trgm`, `pgvector` when semantic retrieval is needed.
- Queue: RabbitMQ + Celery or Dramatiq; Redis + Celery is acceptable locally.
- Cache: Redis.
- File storage: S3-compatible storage, MinIO locally.
- Frontend: Next.js, TypeScript, TanStack Query, React Hook Form.
- Auth: local JWT for demo, OIDC/OAuth2/API keys through replaceable adapters for production.
- Observability: OpenTelemetry, Prometheus, Grafana, Loki, Sentry.
- Delivery: Docker, Docker Compose for local/demo, production-ready container deployment.
- CI/CD: tests, migrations, security scan, OpenAPI validation.

## Engineering Requirements

Every implementation must account for:

- idempotent ingestion and idempotent workers;
- immutable original file storage;
- MIME detection by content, not extension;
- SHA-256 file identity;
- safe ZIP extraction with ZIP Slip and ZIP Bomb protection;
- malware scan status;
- parser versioning and processing run history;
- provenance for every extracted value;
- audit events for user and system actions;
- retry, timeout, dead-letter, heartbeat, and manual retry for worker tasks;
- OpenAPI-documented versioned API under `/api/v1`;
- meaningful error codes and operator-visible failure reasons;
- unit, integration, parser golden, OCR regression, matching quality, API contract, security, and backup/restore tests.

## Ports And Adapters

Business logic must not be coupled directly to infrastructure. Use interfaces/adapters for:

- file storage: local/MinIO/S3/corporate storage;
- identity: local JWT/OIDC/API key/OAuth2 client credentials;
- task dispatch: Celery/RabbitMQ/Redis/company broker;
- service catalog: XLSX/JSON import, REST API, periodic sync;
- publication: pull API, webhook, CSV/XLSX/JSON export;
- observability and notifications.

The domain core should not know where files are stored, how users authenticate, where the service catalog comes from, how events are delivered, or which broker is used.

## Product Boundaries

Build the requested processing component. Do not create a CRM, billing system, public marketplace, new corporate SSO, organization management platform, complex Kubernetes cluster, or separate BI platform unless the company explicitly requires it.

See detailed memory files under `docs/memory/`.
