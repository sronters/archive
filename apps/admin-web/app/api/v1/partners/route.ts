import { NextResponse } from "next/server";

import { partners } from "../../../demo-data";

export function GET() {
  return NextResponse.json({ total: partners.length, items: partners });
}
