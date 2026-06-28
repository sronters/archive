import { NextResponse } from "next/server";

export function POST() {
  return NextResponse.json({ status: "completed", retried: 1, remaining_errors: 0 });
}
