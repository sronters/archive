import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { service_id?: string; task_id?: string };

  if (!body.task_id || !body.service_id) {
    return NextResponse.json(
      { detail: "Поля task_id и service_id обязательны." },
      { status: 422 },
    );
  }

  return NextResponse.json({
    status: "matched",
    task_id: body.task_id,
    service_id: body.service_id,
  });
}
