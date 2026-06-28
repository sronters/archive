"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useState } from "react";

import { metrics as initialMetrics, services, unmatched } from "./demo-data";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

const navItems = [
  ["dashboard", "Дашборд"],
  ["upload", "Загрузка"],
  ["runs", "Запуски"],
  ["review", "Ревью"],
  ["prices", "Цены"],
  ["webhooks", "Вебхуки"],
  ["system", "Система"],
];

const runRows = [
  ["RUN-771", "Клиника 6 прайс 2026.xlsx", "xlsx-stdlib", "извлечено", "5030 строк"],
  ["RUN-772", "Клиника 1 прайс 2024.docx", "docx-ooxml-stdlib", "извлечено", "2720 строк"],
  ["RUN-773", "Клиника 2 прайс 2026.pdf", "pdf-text-adapter", "извлечено", "200 строк"],
];

const initialWebhookRows = [
  ["price_version.created", "integration-primary", "доставлено", "204"],
  ["price_list.needs_review", "ops-monitor", "доставлено", "200"],
  ["price_list.failed", "integration-primary", "повтор", "500"],
];

export default function Page() {
  const [files, setFiles] = useState<File[]>([]);
  const [feedback, setFeedback] = useState("Готово к загрузке документов.");
  const [isProcessing, setIsProcessing] = useState(false);
  const [errors, setErrors] = useState(initialMetrics.errors);
  const [webhookRows, setWebhookRows] = useState(initialWebhookRows);
  const [lastUpdated, setLastUpdated] = useState("только что");

  function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    setFiles(selectedFiles);
    setFeedback(
      selectedFiles.length > 0
        ? `Выбрано файлов: ${selectedFiles.length}. Можно запускать обработку.`
        : "Готово к загрузке документов.",
    );
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (files.length === 0) {
      setFeedback("Сначала выберите ZIP, PDF, DOCX, XLS или XLSX.");
      return;
    }

    setIsProcessing(true);
    setFeedback("Загрузка и проверка форматов...");
    const formData = new FormData(event.currentTarget);
    formData.delete("files");
    files.forEach((file) => formData.append("files", file));

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/ingestion-batches`, {
        body: formData,
        method: "POST",
      });
      const result = (await response.json()) as {
        detail?: string;
        document_count?: number;
      };
      if (!response.ok) {
        throw new Error(result.detail ?? "Не удалось принять документы.");
      }
      setFeedback(`Обработка завершена. Принято документов: ${result.document_count}.`);
      setLastUpdated(new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Ошибка обработки.");
    } finally {
      setIsProcessing(false);
    }
  }

  async function retryFailures() {
    setFeedback("Повторяем ошибочные операции...");
    const response = await fetch(`${apiBaseUrl}/api/v1/system/retry-failures`, {
      method: "POST",
    });
    if (!response.ok) {
      setFeedback("Повтор не выполнен. Проверьте API.");
      return;
    }
    setErrors(0);
    setWebhookRows((rows) =>
      rows.map((row) =>
        row[0] === "price_list.failed"
          ? [row[0], row[1], "доставлено после повтора", "204"]
          : row,
      ),
    );
    setFeedback("Ошибка повторена успешно. Необработанных ошибок нет.");
  }

  function refreshData() {
    setLastUpdated(new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }));
    setFeedback("Данные обновлены.");
  }

  const metricRows = [
    ["Документов получено", String(initialMetrics.documents)],
    ["Позиции извлечены", String(initialMetrics.extractedItems)],
    ["Нужно проверить", String(initialMetrics.reviewQueue)],
    ["Ошибки", String(errors)],
    ["Автосопоставление", `${initialMetrics.normalizationPercent}%`],
    ["Записей справочника", String(initialMetrics.catalogServices)],
  ];
  const reviewRows = unmatched.map((task) => [
    task.task_id,
    task.partner,
    task.service_name_raw,
    task.reason,
    task.priority,
  ]);
  const priceRows = services.map((service) => [
    service.external_service_id,
    service.name,
    service.partner,
    String(service.resident_price_kzt),
    String(service.nonresident_price_kzt),
    service.status,
  ]);

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">MedArchive</div>
        <nav className="nav">
          {navItems.map(([id, label]) => (
            <a href={`#${id}`} key={id}>{label}</a>
          ))}
          <Link href="/docs">Документация</Link>
        </nav>
      </aside>
      <section className="main">
        <header className="toolbar">
          <div>
            <h1 className="title">Операционная панель</h1>
            <p className="subtitle">
              API: <a href="/api/v1/system/status">/api/v1</a> · обновлено {lastUpdated}
            </p>
          </div>
          <div className="toolbarActions">
            <Link className="buttonLink" href="/docs">Документация</Link>
            <button type="button" onClick={retryFailures}>Повторить ошибки</button>
            <a className="buttonLink primary" href="/api/v1/exports/price-versions">
              Экспорт цен
            </a>
          </div>
        </header>

        <div className="feedback" role="status">{feedback}</div>

        <section className="metrics" id="dashboard" aria-label="Метрики обработки">
          {metricRows.map(([label, value]) => (
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
            <form className="uploadBox" onSubmit={handleUpload}>
              <input
                accept=".zip,.pdf,.docx,.xls,.xlsx"
                aria-label="Загрузить прайс-листы"
                multiple
                name="files"
                onChange={handleFiles}
                type="file"
              />
              <div className="fieldGrid">
                <label>
                  Ключ идемпотентности
                  <input defaultValue="clinic-price-2026-06" name="idempotency_key" />
                </label>
                <label>
                  API ключ
                  <input defaultValue="dev-admin" name="api_key" type="password" />
                </label>
              </div>
              <button disabled={isProcessing} type="submit" className="primary">
                {isProcessing ? "Обработка..." : "Начать обработку"}
              </button>
            </form>
          </div>

          <div className="panel" id="system">
            <div className="panelHeader">
              <h2>Статус системы</h2>
              <span>готовность сервисов</span>
            </div>
            <dl className="statusList">
              <div><dt>API</dt><dd>готов</dd></div>
              <div><dt>Workers</dt><dd>3 активны</dd></div>
              <div><dt>Хранилище</dt><dd>готово</dd></div>
              <div><dt>OpenAPI</dt><dd><a href="/openapi.json">доступен</a></dd></div>
            </dl>
          </div>

          <TablePanel
            columns={["Задача", "Партнер", "Извлеченная услуга", "Причина", "Приоритет"]}
            id="review"
            onRefresh={refreshData}
            rows={reviewRows}
            title="Очередь ручной проверки"
          />
          <TablePanel
            columns={["Запуск", "Документ", "Парсер", "Статус", "Результат"]}
            id="runs"
            onRefresh={refreshData}
            rows={runRows}
            title="Запуски обработки"
          />
          <TablePanel
            columns={["Услуга", "Название", "Партнер", "Резидент", "Нерезидент", "Состояние"]}
            id="prices"
            onRefresh={refreshData}
            rows={priceRows}
            title="Опубликованные цены"
          />
          <TablePanel
            columns={["Событие", "Endpoint", "Статус", "HTTP"]}
            id="webhooks"
            onRefresh={refreshData}
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
  onRefresh,
  rows,
  title,
}: {
  columns: string[];
  id: string;
  onRefresh: () => void;
  rows: string[][];
  title: string;
}) {
  return (
    <section className="panel tablePanel" id={id}>
      <div className="panelHeader">
        <h2>{title}</h2>
        <button type="button" onClick={onRefresh}>Обновить</button>
      </div>
      <div className="tableWrap">
        <table>
          <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.join("-")}>
                {row.map((cell) => <td key={cell}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
