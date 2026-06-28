# MedArchive

MedArchive - сервис для автоматической обработки архива прайс-листов клиник-партнеров.

Система принимает ZIP, PDF, DOCX, XLS, XLSX и сканы, извлекает услуги и цены, сопоставляет строки с единым справочником услуг, отправляет спорные позиции оператору и публикует проверенную базу цен через API, экспорт и вебхуки.

## Демо

- Vercel-прототип: https://med-chi-pearl.vercel.app
- Документация Mintlify: `docs-site/`
- Swagger/OpenAPI: `docs-site/openapi.json` или `/docs` при локальном запуске API
- Демо-видео: `outputs/MedArchive_demo_video.webm`
- Презентация: `outputs/MedArchive_hackathon_pitch.pptx`

## Результаты обработки архива

Архив организаторов обработан в preview-режиме.

- Документов: 10
- Форматы: 6 PDF, 1 DOCX, 2 XLSX, 1 XLS
- Извлеченных позиций прайса: 8877
- Записей в сформированном справочнике услуг: 6614
- Успешная нормализация: 99.95%
- Позиции в очереди ручной проверки: 4

Файлы результата:

- `outputs/processed_database_preview.json`
- `outputs/processed_price_items_preview.csv`
- `outputs/service_catalog_seed.json`
- `outputs/quality_report.md`

## Архитектура

```text
apps/
  api/        FastAPI API
  worker/     Celery worker
  admin-web/  Next.js административная панель
packages/
  domain/              доменные сущности и workflow
  application/         use cases и orchestration services
  infrastructure/      SQLAlchemy, storage, queue, auth, adapters
  document_parsers/    адаптеры PDF/DOCX/XLS/XLSX/OCR
  matching/            сопоставление услуг со справочником
  shared/              общие утилиты
migrations/            Alembic migrations
tests/                 тесты
docs/                  контракты и runbooks
docs-site/             Mintlify-документация
outputs/               артефакты сдачи
```

## Быстрый запуск

Требования:

- Python 3.12
- Node.js 24+
- pnpm 10+
- Docker Desktop / Docker Compose v2

Установка зависимостей:

```powershell
py -m pip install -e ".[dev,parsers]"
corepack pnpm install --frozen-lockfile
```

Запуск полного стека:

```bash
make up
```

Загрузка файла или архива через CLI:

```powershell
py -m medarchive_infrastructure.cli ingest ".\prices.zip" --api-url http://localhost:8000
```

Проверки:

```bash
make backend-check
make frontend-check
```

Короткая smoke-проверка:

```bash
py -m pytest tests/test_xlsx_vertical_slice.py tests/test_docx_parser.py tests/test_ingestion_api.py tests/test_api_health.py -q
```

Проверка frontend:

```bash
pnpm --dir apps/admin-web build
```

## API

API версионируется под `/api/v1`.

Ключевые endpoint-ы:

- `POST /api/v1/ingestion-batches`
- `POST /api/v1/service-catalog/imports`
- `POST /api/v1/partners/imports`
- `GET /api/v1/services`
- `GET /api/v1/services/{service_id}/partners`
- `GET /api/v1/partners`
- `GET /api/v1/partners/{partner_id}/services`
- `GET /api/v1/search`
- `GET /api/v1/unmatched`
- `POST /api/v1/match`
- `GET /api/v1/review-tasks`
- `POST /api/v1/review-tasks/{task_id}/claim`
- `POST /api/v1/review-tasks/{task_id}/approve`
- `POST /api/v1/review-tasks/{task_id}/reject`
- `POST /api/v1/review-tasks/{task_id}/correct`
- `GET /api/v1/price-versions`
- `GET /api/v1/exports/price-versions`
- `GET /api/v1/system/status`

## Что реализовано

- загрузка ZIP и отдельных документов;
- безопасная обработка исходных файлов;
- парсеры XLSX, XLS, DOCX, текстового PDF и OCR-граница для сканов;
- извлечение названия услуги, цены резидента и цены нерезидента;
- сопоставление с целевым справочником услуг;
- очередь ручной верификации;
- approve/reject/correct workflow;
- история и версии опубликованных цен;
- JSON/CSV/XLSX экспорт;
- подписанные вебхуки;
- RBAC для операторов и интеграций;
- метрики и runbooks;
- административная панель оператора;
- Swagger/OpenAPI и Mintlify-документация.

## Документация Mintlify

Проверка документации:

```bash
cd docs-site
npx mintlify broken-links
npx mintlify openapi-check openapi.json
```

Результат последней проверки: битых ссылок нет, OpenAPI валиден.

Для публикации подключите репозиторий в Mintlify и укажите root `docs-site`.
