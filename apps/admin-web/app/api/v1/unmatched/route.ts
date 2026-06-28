import { NextResponse } from "next/server";

import { unmatched } from "../../../demo-data";

export function GET() {
  return NextResponse.json({ total: unmatched.length, items: unmatched });
}
