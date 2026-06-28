import { NextRequest, NextResponse } from "next/server";

const supportedExtensions = new Set(["pdf", "docx", "xls", "xlsx", "zip"]);

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const files = formData.getAll("files").filter((value): value is File => value instanceof File);

  if (files.length === 0) {
    return NextResponse.json({ detail: "Добавьте хотя бы один файл." }, { status: 422 });
  }

  const unsupported = files
    .map((file) => file.name)
    .filter((name) => !supportedExtensions.has(name.split(".").pop()?.toLocaleLowerCase() ?? ""));

  if (unsupported.length > 0) {
    return NextResponse.json(
      { detail: `Неподдерживаемые файлы: ${unsupported.join(", ")}` },
      { status: 415 },
    );
  }

  return NextResponse.json(
    {
      batch_id: `batch-${Date.now()}`,
      document_count: files.length,
      status: "processed",
    },
    { status: 202 },
  );
}
