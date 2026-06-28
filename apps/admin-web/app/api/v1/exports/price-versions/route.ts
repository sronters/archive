import { services } from "../../../../demo-data";

export function GET() {
  const header = [
    "external_service_id",
    "service_name",
    "partner",
    "resident_price_kzt",
    "nonresident_price_kzt",
    "status",
  ];
  const rows = services.map((service) => [
    service.external_service_id,
    service.name,
    service.partner,
    service.resident_price_kzt,
    service.nonresident_price_kzt,
    service.status,
  ]);
  const csv = [header, ...rows]
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
    .join("\r\n");

  return new Response(`\uFEFF${csv}`, {
    headers: {
      "Content-Disposition": 'attachment; filename="medarchive-prices.csv"',
      "Content-Type": "text/csv; charset=utf-8",
    },
  });
}
