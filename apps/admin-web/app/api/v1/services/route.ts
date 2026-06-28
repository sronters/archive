import { NextRequest, NextResponse } from "next/server";

import { services } from "../../../demo-data";

export function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim().toLocaleLowerCase("ru") ?? "";
  const items = query
    ? services.filter((service) => service.name.toLocaleLowerCase("ru").includes(query))
    : services;

  return NextResponse.json({ total: items.length, items });
}
