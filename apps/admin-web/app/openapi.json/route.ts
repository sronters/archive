import { NextResponse } from "next/server";

import openApi from "../../../../docs-site/openapi.json";

export function GET() {
  return NextResponse.json(openApi);
}
