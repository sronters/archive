import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const repoRoot = process.cwd();
const tmp = "C:/Users/user/AppData/Local/Temp/codex-presentations/medarchive-hackathon/tmp";
const starterPath = path.join(tmp, "template-starter.pptx");
const out = path.join(repoRoot, "outputs", "MedArchive_hackathon_pitch.pptx");
const previewDir = path.join(repoRoot, "outputs", "pitch-preview");

function shapeBy(slide, predicate) {
  const found = slide.shapes.items.find(predicate);
  if (!found) throw new Error("shape not found");
  return found;
}

function setText(shape, text, fontSize) {
  shape.text = text;
  shape.text.style = { fontSize, color: "#424242", typeface: "Arial" };
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const requireFromTmp = createRequire(path.join(tmp, "package.json"));
const artifactToolPath = requireFromTmp.resolve("@oai/artifact-tool");
const { FileBlob, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);
const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
const slides = presentation.slides.items;

setText(shapeBy(slides[0], (shape) => shape.placeholderType === "title"), "MedArchive", 52);
setText(
  shapeBy(slides[0], (shape) => shape.placeholderType === "subtitle"),
  "Кейс 2: обработка архива прайсов клиник",
  28,
);
setText(
  shapeBy(slides[0], (shape) => shape.name === "Google Shape;57;p1"),
  "Команда <номер>, Караганда 2026",
  18,
);

setText(shapeBy(slides[1], (shape) => shape.placeholderType === "title"), "Ресурсы и результат", 34);
setText(
  shapeBy(slides[1], (shape) => shape.placeholderType === "body"),
  "Ресурсы: ТЗ MedArchive; архив из 10 прайсов клиник; FastAPI; PostgreSQL; Celery/Redis; Next.js; Docker Compose; Swagger/OpenAPI; Mintlify; PyMuPDF/pdfplumber; python-docx; openpyxl; OCR-адаптер.\n\nРезультат: рабочий продуктовый прототип, обработанная база, сформированный справочник услуг, отчет качества, документация API и Vercel-демо: https://med-chi-pearl.vercel.app",
  20,
);

setText(shapeBy(slides[2], (shape) => shape.placeholderType === "title"), "Архитектура", 34);
setText(
  shapeBy(slides[2], (shape) => shape.placeholderType === "body"),
  "Админ-панель / интеграции → FastAPI /api/v1 → PostgreSQL + хранилище исходников → outbox + workers.\n\nАдаптеры парсеров: PDF, DOCX, XLS/XLSX, OCR-граница для сканов.\n\nСопоставление: код услуги, точное название, синонимы, fuzzy-кандидаты. Спорные строки идут в очередь проверки.\n\nВыход: поиск API, экспорт CSV/XLSX/JSON, вебхуки, версии цен.",
  21,
);

setText(shapeBy(slides[3], (shape) => shape.placeholderType === "title"), "Метрики качества", 34);
setText(
  shapeBy(slides[3], (shape) => shape.placeholderType === "body"),
  "Демо-архив: 10 документов — 6 PDF, 1 DOCX, 2 XLSX, 1 XLS.\n\nОбработанная база: 8877 извлеченных позиций прайса, 6614 записей справочника услуг.\n\nУспешная нормализация: 99.95%; очередь ручной проверки: 4 позиции.\n\nПроверки: backend 8 passed / 1 skipped; frontend build passed; Mintlify OpenAPI valid; Vercel deploy READY.",
  21,
);

setText(shapeBy(slides[4], (shape) => shape.placeholderType === "title"), "Демо прототипа", 34);
setText(
  shapeBy(slides[4], (shape) => shape.placeholderType === "body"),
  "1. Vercel-панель: дашборд, загрузка, статусы обработки.\n2. Swagger/OpenAPI: /services, /partners, /search, /unmatched, /match и API загрузки/ревью/экспорта.\n3. Outputs: обработанная база и справочник услуг.\n4. Ревью: оператор подтверждает, исправляет или отклоняет строку.\n5. Публикация: версии цен, экспорт, вебхуки.",
  22,
);

setText(shapeBy(slides[5], (shape) => shape.placeholderType === "title"), "Что сдаем", 34);
setText(
  shapeBy(slides[5], (shape) => shape.placeholderType === "body"),
  "GitHub: ветка initial-backend-fixes.\nПрототип: https://med-chi-pearl.vercel.app\nДокументация: docs-site/ + openapi.json для Mintlify.\nДанные: processed_database_preview.json, processed_price_items_preview.csv, service_catalog_seed.json.\nОтчет и демо: quality_report.md, SUBMISSION.md, MedArchive_demo_video.webm.",
  22,
);

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(path.join(previewDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(out);
console.log(out);
