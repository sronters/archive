const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const navItems = [
  ["dashboard", "Дашборд"],
  ["upload", "Загрузка"],
  ["batches", "Пакеты"],
  ["documents", "Документы"],
  ["runs", "Запуски"],
  ["review", "Ревью"],
  ["catalog", "Справочник"],
  ["partners", "Партнеры"],
  ["prices", "Цены"],
  ["history", "История"],
  ["exports", "Экспорт"],
  ["webhooks", "Вебхуки"],
  ["system", "Система"],
];

const metrics = [
  ["Документов получено", "10"],
  ["Позиции извлечены", "8877"],
  ["Нужно проверить", "4"],
  ["Ошибки", "1"],
  ["Автосопоставление", "99.95%"],
  ["Записей справочника", "6614"],
];

const reviewRows = [
  ["RT-1042", "Клиника 1", "CHECK-UP", "нет цены", "Высокий"],
  ["RT-1043", "Клиника 1", "Диагностика инфекционных заболеваний", "нет цены", "Средний"],
  ["RT-1044", "Клиника 1", "Микробиологические исследования", "нет цены", "Средний"],
];

const priceRows = [
  ["svc-0001", "Консультация терапевта", "Клиника 1", "7000", "9000", "опубликовано"],
  ["svc-0014", "МРТ головного мозга", "Клиника 2", "25000", "32000", "опубликовано"],
  ["svc-0078", "УЗИ брюшной полости", "Клиника 6", "12000", "15000", "проверено"],
];

const runRows = [
  ["RUN-771", "Клиника 6 прайс 2026.xlsx", "xlsx-stdlib", "EXTRACTED", "5030 строк"],
  ["RUN-772", "Клиника 1 прайс 2024.docx", "docx-ooxml-stdlib", "EXTRACTED", "2720 строк"],
  ["RUN-773", "Клиника 2 прайс 2026.pdf", "pdf-text-adapter", "EXTRACTED", "200 строк"],
];

const webhookRows = [
  ["price_version.created", "integration-primary", "доставлено", "204"],
  ["price_list.needs_review", "ops-monitor", "доставлено", "200"],
  ["price_list.failed", "integration-primary", "повтор", "500"],
];

export default function Page() {
  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">MedArchive</div>
        <nav className="nav">
          {navItems.map(([id, label]) => (
            <a href={`#${id}`} key={id}>
              {label}
            </a>
          ))}
        </nav>
      </aside>
      <section className="main">
        <header className="toolbar">
          <div>
            <h1 className="title">Операционная панель</h1>
            <p className="subtitle">{apiBaseUrl}/api/v1</p>
          </div>
          <div className="toolbarActions">
            <button type="button">Повторить ошибки</button>
            <button type="button" className="primary">
              Экспорт цен
            </button>
          </div>
        </header>

        <section className="metrics" id="dashboard" aria-label="Метрики обработки">
          {metrics.map(([label, value]) => (
            <div className="metric" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </section>

        <section className="workbench">
          <div className="panel" id="upload">
            <div className="panelHeader">
              <h2>Загрузка</h2>
              <span>ZIP, PDF, DOCX, XLS, XLSX</span>
            </div>
            <div className="uploadBox">
              <input aria-label="Загрузить прайс-листы" type="file" multiple />
              <div className="fieldGrid">
                <label>
                  Ключ идемпотентности
                  <input defaultValue="clinic-price-2026-06" />
                </label>
                <label>
                  API ключ
                  <input defaultValue="dev-admin" type="password" />
                </label>
              </div>
              <button type="button" className="primary">
                Начать обработку
              </button>
            </div>
          </div>

          <div className="panel" id="system">
            <div className="panelHeader">
              <h2>Статус системы</h2>
              <span>готовность сервисов</span>
            </div>
            <dl className="statusList">
              <div>
                <dt>API</dt>
                <dd>готов</dd>
              </div>
              <div>
                <dt>Workers</dt>
                <dd>3 активны</dd>
              </div>
              <div>
                <dt>Хранилище</dt>
                <dd>MinIO настроен</dd>
              </div>
              <div>
                <dt>Синхронизация справочника</dt>
                <dd>remote_api включен</dd>
              </div>
            </dl>
          </div>

          <TablePanel
            columns={["Задача", "Партнер", "Извлеченная услуга", "Причина", "Приоритет"]}
            id="review"
            rows={reviewRows}
            title="Очередь ручной проверки"
          />
          <TablePanel
            columns={["Запуск", "Документ", "Парсер", "Статус", "Результат"]}
            id="runs"
            rows={runRows}
            title="Запуски обработки"
          />
          <TablePanel
            columns={["Услуга", "Название", "Партнер", "Резидент", "Нерезидент", "Состояние"]}
            id="prices"
            rows={priceRows}
            title="Опубликованные цены"
          />
          <TablePanel
            columns={["Событие", "Endpoint", "Статус", "HTTP"]}
            id="webhooks"
            rows={webhookRows}
            title="Доставка вебхуков"
          />
        </section>
      </section>
    </main>
  );
}

function TablePanel({
  columns,
  id,
  rows,
  title,
}: {
  columns: string[];
  id: string;
  rows: string[][];
  title: string;
}) {
  return (
    <section className="panel tablePanel" id={id}>
      <div className="panelHeader">
        <h2>{title}</h2>
        <button type="button">Обновить</button>
      </div>
      <div className="tableWrap">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.join("-")}>
                {row.map((cell) => (
                  <td key={cell}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
