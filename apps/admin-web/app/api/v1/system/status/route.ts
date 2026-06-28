import { NextResponse } from "next/server";

import { metrics } from "../../../../demo-data";

export function GET() {
  return NextResponse.json({
    status: "ready",
    api_namespace: "/api/v1",
    storage: "ready",
    workers: 3,
    metrics,
  });
}
