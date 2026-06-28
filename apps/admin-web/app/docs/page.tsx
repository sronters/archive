import Link from "next/link";

const apiEndpoints = [
  ["GET", "/api/v1/services", "поиск услуг в сформированном справочнике"],
  ["GET", "/api/v1/services/{service_id}/partners", "цены услуги по партнерам"],
  ["GET", "/api/v1/partners", "список клиник-партнеров"],
  ["GET", "/api/v1/partners/{partner_id}/services", "прайс конкретного партнера"],
  ["GET", "/api/v1/search", "единый поиск по услугам и партнерам"],
  ["GET", "/api/v1/unmatched", "позиции в очереди ручной проверки"],
  ["POST", "/api/v1/match", "ручное подтверждение сопоставления"],
];

const deliverables = [
  ["Рабочий MVP", "репозиторий, Vercel-прототип и инструкция запуска"],
  ["Обработанная база", "8877 извлеченных позиций из 10 документов"],
  ["Справочник услуг", "6614 нормализованных записей"],
  ["API-документация", "OpenAPI/Swagger и эта страница документации"],
  ["Отчет качества", "99.95% успешной нормализации, 4 позиции в очереди"],
  ["Демо-материалы", "презентация, видео и скриншоты пользовательского сценария"],
];

export default function DocsPage() {
  return (
    <main className="docsPage">
      <header className="docsHeader">
        <Link className="backLink" href="/">
          ← Панель
        </Link>
        <h1>Документация MedArchive</h1>
        <p>
          Система принимает архив прайс-листов клиник, извлекает услуги и цены,
          сопоставляет их со справочником, отправляет спорные строки на проверку
          и публикует проверенную базу через API, экспорт и вебхуки.
        </p>
      </header>

      <section className="docsGrid">
        <article className="docsBlock">
          <h2>Что сдано</h2>
          <ul>
            {deliverables.map(([title, text]) => (
              <li key={title}>
                <strong>{title}</strong>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="docsBlock">
          <h2>Результаты обработки</h2>
          <dl className="docsStats">
            <div>
              <dt>Документов</dt>
              <dd>10</dd>
            </div>
            <div>
              <dt>Извлеченных позиций</dt>
              <dd>8877</dd>
            </div>
            <div>
              <dt>Успешная нормализация</dt>
              <dd>99.95%</dd>
            </div>
            <div>
              <dt>Очередь проверки</dt>
              <dd>4</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="docsBlock">
        <h2>Быстрый запуск</h2>
        <pre>{`git clone https://github.com/sronters/archive.git
cd archive
pnpm install --frozen-lockfile
pnpm --dir apps/admin-web build
py -m pytest tests/test_xlsx_vertical_slice.py tests/test_docx_parser.py tests/test_ingestion_api.py tests/test_api_health.py -q`}</pre>
      </section>

      <section className="docsBlock">
        <h2>API</h2>
        <div className="endpointList">
          {apiEndpoints.map(([method, path, text]) => (
            <div className="endpoint" key={path}>
              <code>{method}</code>
              <span>{path}</span>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="docsBlock">
        <h2>Архитектура</h2>
        <p>
          Backend построен на FastAPI и доменной модели обработки документов.
          Парсеры работают с PDF, DOCX, XLS и XLSX, слой matching нормализует
          услуги, очередь ревью сохраняет спорные позиции, а публикация цен
          доступна через версии, экспорт и интеграционные события.
        </p>
        <pre>{`Документ -> Парсер -> Нормализация -> Сопоставление -> Ревью -> Публикация -> API/Экспорт/Вебхуки`}</pre>
      </section>

      <section className="docsBlock">
        <h2>Артефакты в репозитории</h2>
        <ul>
          <li><code>outputs/processed_database_preview.json</code> — обработанная база</li>
          <li><code>outputs/service_catalog_seed.json</code> — справочник услуг</li>
          <li><code>outputs/quality_report.md</code> — отчет качества</li>
          <li><code>outputs/MedArchive_hackathon_pitch.pptx</code> — презентация</li>
          <li><code>outputs/MedArchive_demo_video.webm</code> — демо-видео</li>
          <li><code>docs-site/</code> — исходники Mintlify-документации</li>
        </ul>
      </section>
    </main>
  );
}
