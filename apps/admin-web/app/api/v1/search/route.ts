import { NextRequest, NextResponse } from "next/server";

import { partners, services } from "../../../demo-data";

export function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim().toLocaleLowerCase("ru") ?? "";
  const serviceResults = services.filter((service) =>
    service.name.toLocaleLowerCase("ru").includes(query),
  );
  const partnerResults = partners.filter((partner) =>
    partner.name.toLocaleLowerCase("ru").includes(query),
  );

  return NextResponse.json({
    query,
    total: serviceResults.length + partnerResults.length,
    services: serviceResults,
    partners: partnerResults,
  });
}
