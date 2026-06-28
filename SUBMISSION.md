# MedArchive: пакет сдачи хакатона

## Что сдаем

- GitHub: `https://github.com/sronters/archive` ветка `initial-backend-fixes`
- Рабочий прототип: https://med-chi-pearl.vercel.app
- Документация API: Swagger/FastAPI `/docs` и Mintlify-проект в `docs-site/`
- Обработанная база: `outputs/processed_database_preview.json`
- CSV-выгрузка обработанных позиций: `outputs/processed_price_items_preview.csv`
- Сформированный справочник услуг: `outputs/service_catalog_seed.json`
- Отчет качества: `outputs/quality_report.md`
- Презентация: `outputs/MedArchive_hackathon_pitch.pptx`
- Демо-видео: `outputs/MedArchive_demo_video.webm`

## Сообщение для отправки

```text
Команда <номер команды>

Кейс 2: MedArchive / MedPartners
GitHub: https://github.com/sronters/archive/tree/initial-backend-fixes
Прототип: https://med-chi-pearl.vercel.app
Документация: папка docs-site/ или Mintlify URL
Обработанная база: outputs/processed_database_preview.json
Отчет качества: outputs/quality_report.md
Презентация: outputs/MedArchive_hackathon_pitch.pptx
Демо-видео: outputs/MedArchive_demo_video.webm
```

## Питч на 1 минуту

MedPartners получает прайс-листы клиник в разных форматах: PDF, сканированный PDF, DOCX, XLS и XLSX. Вручную это обрабатывается долго: у каждой клиники свои таблицы, названия услуг, даты, цены для резидентов и нерезидентов.

MedArchive автоматизирует этот процесс. Система принимает архив, сохраняет исходники, извлекает строки прайса, связывает услуги с единым справочником, проверяет цены, отправляет спорные позиции оператору и публикует проверенную базу цен через API, экспорт и вебхуки.

Ценность продукта - не просто разбор файлов, а проверенная база цен с историей, происхождением каждой строки и готовыми интеграциями для компании.

## План демо на 2 минуты

1. Открыть Vercel-прототип и показать дашборд.
2. Показать загрузку ZIP/PDF/DOCX/XLS/XLSX.
3. Показать запуски обработки и статусы документов.
4. Показать очередь ручной верификации.
5. Показать опубликованные цены и экспорт.
6. Открыть Swagger/OpenAPI или Mintlify-документацию.

## Архив организаторов

`C:\Users\user\Downloads\Telegram Desktop\Хакатон\Хакатон` содержит 10 прайс-листов:

- 6 PDF
- 1 DOCX
- 2 XLSX
- 1 XLS

## Результаты обработки

- Извлеченных позиций прайса: 8877
- Записей в справочнике услуг: 6614
- Успешная нормализация: 99.95%
- Позиции в очереди ручной проверки: 4
- Обработанная база: `outputs/processed_database_preview.json`
- CSV preview: `outputs/processed_price_items_preview.csv`
- Справочник услуг: `outputs/service_catalog_seed.json`
- Отчет качества: `outputs/quality_report.md`

## Проверка

Backend smoke:

```powershell
py -m pytest tests/test_xlsx_vertical_slice.py tests/test_docx_parser.py tests/test_ingestion_api.py tests/test_api_health.py -q
```

Результат:

```text
8 passed, 1 skipped
```

Frontend build:

```powershell
pnpm --dir apps/admin-web build
```

Результат: успешно.

Mintlify docs:

```powershell
cd docs-site
npx mintlify broken-links
npx mintlify openapi-check openapi.json
```

Результат: битых ссылок нет; OpenAPI валиден.

Примечание: тест текстового PDF требует optional parser extra с `fitz` / PyMuPDF в текущем окружении. Полный production-прогон нужно запускать через Docker Compose с подключенными parser/OCR extras.

## Деплой

Production URL:

```text
https://med-chi-pearl.vercel.app
```

Повторный деплой:

```powershell
npx.cmd vercel --prod --yes
```

Настройки Vercel:

- Framework: Next.js
- Build command: `pnpm --dir apps/admin-web build`
- Output directory: `apps/admin-web/.next`
- Install command: `pnpm install --frozen-lockfile`

Mintlify: подключить репозиторий в Mintlify и указать docs root `docs-site`.
