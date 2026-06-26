const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const navItems = [
  "Dashboard",
  "Upload",
  "Batches",
  "Documents",
  "Runs",
  "Review",
  "Catalog",
  "Partners",
  "Prices",
  "History",
  "Exports",
  "Webhooks",
  "System",
];

const metrics = [
  ["Documents received", "128"],
  ["Completed", "113"],
  ["Needs review", "14"],
  ["Failed", "1"],
  ["Auto-match coverage", "86.4%"],
  ["Correction rate", "1.1%"],
];

const reviewRows = [
  ["RT-1042", "Astana Clinic", "MRI golovnogo mozga", "2 candidates", "High"],
  ["RT-1043", "Medline", "Konsultacia terapevta", "price anomaly", "Medium"],
  ["RT-1044", "Dostar Med", "UZI OBP", "partner unresolved", "High"],
];

const priceRows = [
  ["svc-001", "MRI brain", "clinic-001", "25000", "32000", "published"],
  ["svc-014", "Therapist consultation", "clinic-022", "7000", "9000", "published"],
  ["svc-078", "Abdominal ultrasound", "clinic-017", "12000", "15000", "verified"],
];

const runRows = [
  ["RUN-771", "price-june.xlsx", "xlsx-stdlib", "EXTRACTED", "42 rows"],
  ["RUN-772", "clinic-scan.pdf", "pdf-ocr-adapter", "NEEDS_REVIEW", "18 rows"],
  ["RUN-773", "partner-table.docx", "docx-ooxml-stdlib", "VERIFIED", "9 rows"],
];

const webhookRows = [
  ["price_version.created", "integration-primary", "delivered", "204"],
  ["price_list.needs_review", "ops-monitor", "delivered", "200"],
  ["price_list.failed", "integration-primary", "retryable", "500"],
];

export default function Page() {
  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">MedArchive</div>
        <nav className="nav">
          {navItems.map((item) => (
            <a href={`#${item.toLowerCase()}`} key={item}>
              {item}
            </a>
          ))}
        </nav>
      </aside>
      <section className="main">
        <header className="toolbar">
          <div>
            <h1 className="title">Operations console</h1>
            <p className="subtitle">{apiBaseUrl}/api/v1</p>
          </div>
          <div className="toolbarActions">
            <button type="button">Retry failed</button>
            <button type="button" className="primary">
              Export prices
            </button>
          </div>
        </header>

        <section className="metrics" aria-label="Processing metrics">
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
              <h2>Upload</h2>
              <span>ZIP, PDF, DOCX, XLS, XLSX</span>
            </div>
            <div className="uploadBox">
              <input aria-label="Upload price list documents" type="file" multiple />
              <div className="fieldGrid">
                <label>
                  Idempotency key
                  <input defaultValue="clinic-price-2026-06" />
                </label>
                <label>
                  API key
                  <input defaultValue="dev-admin" type="password" />
                </label>
              </div>
              <button type="button" className="primary">
                Start ingestion
              </button>
            </div>
          </div>

          <div className="panel" id="system">
            <div className="panelHeader">
              <h2>System status</h2>
              <span>readiness surface</span>
            </div>
            <dl className="statusList">
              <div>
                <dt>API</dt>
                <dd>ready</dd>
              </div>
              <div>
                <dt>Workers</dt>
                <dd>3 active</dd>
              </div>
              <div>
                <dt>Storage</dt>
                <dd>MinIO configured</dd>
              </div>
              <div>
                <dt>Catalog sync</dt>
                <dd>remote_api enabled</dd>
              </div>
            </dl>
          </div>

          <TablePanel
            columns={["Task", "Partner", "Extracted service", "Reason", "Priority"]}
            id="review"
            rows={reviewRows}
            title="Review queue"
          />
          <TablePanel
            columns={["Run", "Document", "Parser", "Status", "Output"]}
            id="runs"
            rows={runRows}
            title="Processing runs"
          />
          <TablePanel
            columns={["Service", "Name", "Partner", "Resident", "Non-resident", "State"]}
            id="prices"
            rows={priceRows}
            title="Published prices"
          />
          <TablePanel
            columns={["Event", "Endpoint", "Status", "HTTP"]}
            id="webhooks"
            rows={webhookRows}
            title="Webhook deliveries"
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
        <button type="button">Refresh</button>
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
