"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

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

const evidenceRows = [
  ["File", "clinic-price-2026.pdf"],
  ["Page / row", "17 / 42"],
  ["BBox", "x=124 y=442 w=96 h=18"],
  ["Parser", "pdf-pymupdf-text 0.1.0"],
  ["Confidence", "98.4%"],
  ["Operator", "confirmed"],
];

const diffRows = [
  ["MRI brain", "22000", "29000", "+31.8%", "changed"],
  ["CT chest", "18000", "150000", "+733.3%", "anomaly"],
  ["Pediatric consult", "-", "7000", "-", "new_service"],
];

type GraphApiResponse = {
  nodes: Array<{id: string; type: string; label: string}>;
  edges: Array<{source: string; target: string; type: string}>;
};

export default function Page() {
  const [apiKey, setApiKey] = useState("dev-admin");
  const [status, setStatus] = useState("idle");
  const [searchQuery, setSearchQuery] = useState("MRI");
  const [reviewCount, setReviewCount] = useState("pending");
  const [priceCount, setPriceCount] = useState("pending");
  const [systemStatus, setSystemStatus] = useState("unknown");
  const [graphStatus, setGraphStatus] = useState("demo graph");
  const [graphData, setGraphData] = useState<GraphApiResponse>(demoGraph);

  async function apiFetch(path: string, init?: RequestInit) {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        "X-API-Key": apiKey,
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response;
  }

  async function refreshOperations() {
    setStatus("refreshing");
    try {
      const [system, review, prices] = await Promise.all([
        fetch(`${apiBaseUrl}/api/v1/system/status`),
        apiFetch("/api/v1/review-tasks"),
        apiFetch("/api/v1/price-versions"),
      ]);
      const systemBody = (await system.json()) as { status: string };
      const reviewBody = (await review.json()) as unknown[];
      const priceBody = (await prices.json()) as unknown[];
      setSystemStatus(systemBody.status);
      setReviewCount(String(reviewBody.length));
      setPriceCount(String(priceBody.length));
      setStatus("ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "request failed");
    }
  }

  async function uploadDocuments(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("documents");
    if (!(input instanceof HTMLInputElement) || input.files === null || input.files.length === 0) {
      setStatus("select files first");
      return;
    }
    const body = new FormData();
    Array.from(input.files).forEach((file) => body.append("files", file));
    setStatus("uploading");
    try {
      await apiFetch("/api/v1/ingestion-batches", {
        method: "POST",
        body,
        headers: {"Idempotency-Key": `admin-${Date.now()}`},
      });
      setStatus("uploaded");
      form.reset();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "upload failed");
    }
  }

  async function exportPrices() {
    setStatus("exporting");
    try {
      const response = await apiFetch("/api/v1/exports/price-versions?format=xlsx");
      await response.arrayBuffer();
      setStatus("export ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "export failed");
    }
  }

  async function loadGraph() {
    setGraphStatus("loading graph");
    try {
      const response = await apiFetch(
        "/api/v1/graph/services/00000000-0000-0000-0000-000000000001/neighborhood?depth=2",
      );
      const body = (await response.json()) as GraphApiResponse;
      setGraphData(body.nodes.length > 0 ? body : demoGraph);
      setGraphStatus(body.nodes.length > 0 ? "live graph" : "demo graph");
    } catch (error) {
      setGraphData(demoGraph);
      setGraphStatus(error instanceof Error ? error.message : "graph unavailable");
    }
  }

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
            <input
              aria-label="API key"
              onChange={(event) => setApiKey(event.target.value)}
              type="password"
              value={apiKey}
            />
            <button onClick={refreshOperations} type="button">
              Refresh
            </button>
            <button className="primary" onClick={exportPrices} type="button">
              Export prices
            </button>
          </div>
        </header>

        <section className="metrics" aria-label="Processing metrics">
          {metrics.map(([label, value]) => (
          <div className="metric" key={label}>
              <span>{label}</span>
              <strong>
                {label === "Needs review" ? reviewCount : label === "Completed" ? priceCount : value}
              </strong>
            </div>
          ))}
        </section>

        <section className="workbench">
          <div className="panel" id="upload">
            <div className="panelHeader">
              <h2>Upload</h2>
              <span>ZIP, PDF, DOCX, XLS, XLSX</span>
            </div>
            <form className="uploadBox" onSubmit={uploadDocuments}>
              <input aria-label="Upload price list documents" name="documents" type="file" multiple />
              <div className="fieldGrid">
                <label>
                  Idempotency key
                  <input defaultValue="clinic-price-2026-06" />
                </label>
                <label>
                  Service search
                  <input
                    onChange={(event) => setSearchQuery(event.target.value)}
                    value={searchQuery}
                  />
                </label>
              </div>
              <button type="submit" className="primary">
                Start ingestion
              </button>
            </form>
          </div>

          <div className="panel" id="system">
            <div className="panelHeader">
              <h2>System status</h2>
              <span>readiness surface</span>
            </div>
            <dl className="statusList">
              <div>
                <dt>API</dt>
                <dd>{systemStatus}</dd>
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
                <dd>{status}</dd>
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
          <TablePanel
            columns={["Evidence", "Value"]}
            id="evidence"
            rows={evidenceRows}
            title="Evidence pane"
          />
          <TablePanel
            columns={["Service", "Previous", "Current", "Change", "Status"]}
            id="history"
            rows={diffRows}
            title="Price diff"
          />
          <GraphPanel graph={graphData} onRefresh={loadGraph} status={graphStatus} />
        </section>
      </section>
    </main>
  );
}

function GraphPanel({
  graph,
  onRefresh,
  status,
}: {
  graph: GraphApiResponse;
  onRefresh: () => void;
  status: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let destroyed = false;
    let destroy: (() => void) | undefined;

    async function renderGraph() {
      if (containerRef.current === null) {
        return;
      }
      const cytoscape = (await import("cytoscape")).default;
      if (destroyed || containerRef.current === null) {
        return;
      }
      const cy = cytoscape({
        container: containerRef.current,
        elements: [
          ...graph.nodes.map((node) => ({
            data: {id: node.id, label: node.label, type: node.type},
          })),
          ...graph.edges.map((edge) => ({
            data: {
              id: `${edge.source}-${edge.type}-${edge.target}`,
              source: edge.source,
              target: edge.target,
              label: edge.type,
            },
          })),
        ],
        layout: {name: "breadthfirst", directed: true, padding: 20},
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#0f766e",
              color: "#17202a",
              label: "data(label)",
              "font-size": 10,
              "text-valign": "bottom",
              "text-margin-y": 6,
              width: 28,
              height: 28,
            },
          },
          {
            selector: "edge",
            style: {
              "curve-style": "bezier",
              "line-color": "#9aa4b2",
              "target-arrow-color": "#9aa4b2",
              "target-arrow-shape": "triangle",
              label: "data(label)",
              "font-size": 8,
            },
          },
        ],
      });
      destroy = () => cy.destroy();
    }

    void renderGraph();
    return () => {
      destroyed = true;
      destroy?.();
    };
  }, [graph]);

  return (
    <section className="panel tablePanel" id="graph">
      <div className="panelHeader">
        <h2>Graph neighborhood</h2>
        <div className="toolbarActions">
          <span>{status}</span>
          <button onClick={onRefresh} type="button">
            Refresh
          </button>
        </div>
      </div>
      <div aria-label="Service graph visualization" className="graphCanvas" ref={containerRef} />
    </section>
  );
}

const demoGraph: GraphApiResponse = {
  nodes: [
    {id: "Category:diagnostics", type: "ServiceCategory", label: "Diagnostics"},
    {id: "Service:svc-001", type: "Service", label: "MRI brain"},
    {id: "Partner:clinic-001", type: "Partner", label: "Medical Center"},
    {id: "Raw:mr-head", type: "RawServiceName", label: "MR tomographiya golovy"},
    {id: "Document:doc-001", type: "PriceDocument", label: "price-2026.pdf"},
    {id: "PriceVersion:pv-001", type: "PriceVersion", label: "25 000 KZT"},
  ],
  edges: [
    {source: "Service:svc-001", target: "Category:diagnostics", type: "BELONGS_TO"},
    {source: "Partner:clinic-001", target: "Service:svc-001", type: "OFFERS"},
    {source: "Raw:mr-head", target: "Service:svc-001", type: "CONFIRMED_AS"},
    {source: "Service:svc-001", target: "PriceVersion:pv-001", type: "HAS_PRICE"},
    {source: "PriceVersion:pv-001", target: "Document:doc-001", type: "EXTRACTED_FROM"},
  ],
};

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
