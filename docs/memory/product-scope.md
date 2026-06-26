# Product Scope Memory

## Правильный Объем

MedArchive должен выполнить ровно бизнес-задачу ТЗ, но выполнить ее как подключаемый production-компонент, а не одноразовый хакатонный скрипт.

Формула:

```text
Полный функционал ТЗ
+ реальные обработчики документов
+ надежность
+ интеграционные контракты
+ заменяемые адаптеры
- ненужная собственная экосистема
```

## Must Build

Обязательно реализовать:

- полный processing pipeline;
- загрузку ZIP, PDF, DOCX, XLS/XLSX;
- безопасную распаковку архивов;
- прямое извлечение из PDF/DOCX/XLSX;
- OCR для сканов;
- гибридное извлечение таблиц;
- импорт целевого справочника услуг;
- сопоставление услуг со справочником;
- очередь ручной верификации;
- историю цен и версионирование;
- хранение происхождения каждого результата;
- API;
- OpenAPI;
- административный интерфейс;
- поиск по услугам, партнерам и ценам;
- экспорт JSON/XLSX/CSV;
- webhook после публикации;
- Docker Compose;
- тесты;
- конфигурацию интеграций;
- документацию подключения и эксплуатации.

## Must Not Build Without Company Requirement

Не строить без явного требования компании:

- собственную CRM;
- собственную биллинговую систему;
- собственное управление организациями;
- новый корпоративный SSO;
- публичный маркетплейс клиник;
- сложный Kubernetes-кластер;
- десятки сервисов;
- отдельную аналитическую платформу;
- мобильное приложение;
- замену существующего сайта или личного кабинета компании.

## Product Boundary

Inside MedArchive:

- прием документов;
- OCR и парсинг;
- определение клиники и даты прайса;
- извлечение услуг и цен;
- разделение цены резидента и нерезидента;
- сопоставление с предоставленным справочником;
- автоматические проверки;
- очередь ручной верификации;
- версионирование цен;
- provenance;
- API получения результатов;
- экспорт обработанных данных.

Outside MedArchive:

- CRM компании;
- основной каталог клиник, если он уже есть;
- корпоративная IAM/SSO как источник истины;
- биллинг;
- публичная витрина;
- BI;
- корпоративные уведомления;
- корпоративная лог-платформа.

MedArchive подключается к внешним системам через adapters and configuration.

## Integration Requirements

Service catalog:

- file upload from XLSX/JSON for demo and fallback;
- company REST API mode;
- periodic sync mode.

Partners:

- keep internal `partner_id`;
- keep `external_partner_id` from company systems;
- never force company systems to adopt MedArchive identifiers.

Publication:

- pull API, for example prices by external partner or offers by external service;
- webhook `price_list.published`;
- export to CSV, XLSX, JSON, or ZIP with reports and errors.

Authentication:

- demo: local users plus JWT;
- production: OIDC/corporate SSO;
- machine-to-machine: API key or OAuth2 client credentials.

File storage:

- local development: MinIO;
- production: S3, corporate object storage, or approved file storage.

Queue:

- local: Redis + Celery can be acceptable;
- production: RabbitMQ + Celery, Dramatiq, or an existing company broker;
- business logic must depend on `TaskDispatcher` interface, not Celery directly.

## Company Questions To Preserve

Before final production integration, clarify:

- where partners, services, and prices are stored now;
- whether the existing system has an API;
- which identifiers are used for clinics and services;
- whether results must be written back to their database;
- which authorization model they use;
- which infrastructure they have: cloud, servers, Docker, Kubernetes;
- whether PostgreSQL, S3, RabbitMQ, Redis, or equivalents already exist;
- how price lists arrive today: email, personal cabinet, manual upload, SFTP;
- who verifies results;
- whether publication requires one or two approvals;
- expected volume by documents, pages, clinics, and services;
- whether cloud OCR is allowed;
- whether documents contain personal or medical data;
- whether CRM, ERP, HIS, or website integration is required;
- preferred result format: API, JSON, XLSX, webhook.

## UI Scope

Admin UI must support:

- upload and batch status;
- document status and errors;
- review queue;
- side-by-side source fragment and extracted data;
- manual approve/reject/correct workflow;
- service search and candidate selection;
- partner price page;
- basic operational dashboard.

The UI should be deployable standalone or embedded behind the company reverse proxy, iframe, microfrontend, or API-only integration depending on company needs.
