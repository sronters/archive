import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const repoRoot = process.cwd();
const outputDir = path.join(repoRoot, "outputs", "demo-video");
await fs.mkdir(outputDir, { recursive: true });
for (const file of await fs.readdir(outputDir)) {
  if (file.endsWith(".webm")) {
    await fs.rm(path.join(outputDir, file), { force: true });
  }
}
await fs.rm(path.join(repoRoot, "outputs", "MedArchive_demo_video.webm"), { force: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1366, height: 768 },
  recordVideo: { dir: outputDir, size: { width: 1366, height: 768 } },
});
const page = await context.newPage();

async function caption(text) {
  await page.evaluate((value) => {
    let el = document.getElementById("demo-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "demo-caption";
      el.style.position = "fixed";
      el.style.left = "24px";
      el.style.bottom = "24px";
      el.style.zIndex = "999999";
      el.style.maxWidth = "760px";
      el.style.padding = "14px 18px";
      el.style.borderRadius = "8px";
      el.style.background = "rgba(15, 23, 42, 0.92)";
      el.style.color = "white";
      el.style.font = "600 22px Arial, sans-serif";
      el.style.boxShadow = "0 8px 28px rgba(0,0,0,.25)";
      document.body.appendChild(el);
    }
    el.textContent = value;
  }, text);
  await page.waitForTimeout(2200);
}

await page.goto("https://med-chi-pearl.vercel.app", { waitUntil: "networkidle" });
await caption("MedArchive: рабочий Vercel-прототип для обработки прайсов клиник");
await page.screenshot({ path: path.join(outputDir, "01-vercel-dashboard.png"), fullPage: true });

await caption("Дашборд: документы, извлеченные позиции, ручная проверка и автосопоставление");
await page.locator("#upload").scrollIntoViewIfNeeded();
await caption("Загрузка: ZIP, PDF, DOCX, XLS, XLSX и ключ идемпотентности");
await page.screenshot({ path: path.join(outputDir, "02-upload.png"), fullPage: true });

await page.locator("#review").scrollIntoViewIfNeeded();
await caption("Очередь проверки: оператор подтверждает, исправляет или отклоняет спорные строки");
await page.screenshot({ path: path.join(outputDir, "03-review.png"), fullPage: true });

await page.locator("#prices").scrollIntoViewIfNeeded();
await caption("Опубликованные цены: резидент, нерезидент, статус и экспорт");
await page.screenshot({ path: path.join(outputDir, "04-prices.png"), fullPage: true });

await page.goto(`file://${repoRoot.replaceAll("\\", "/")}/outputs/quality_report.md`);
await caption("Отчет качества: 10 документов, 8877 извлеченных позиций, 4 позиции в очереди");
await page.screenshot({ path: path.join(outputDir, "05-quality-report.png"), fullPage: true });

await page.goto(`file://${repoRoot.replaceAll("\\", "/")}/docs-site/index.mdx`);
await caption("Документация Mintlify: docs-site и сгенерированный OpenAPI");
await page.screenshot({ path: path.join(outputDir, "06-docs-source.png"), fullPage: true });

await page.close();
await context.close();
await browser.close();

const files = await fs.readdir(outputDir);
const webm = files.find((file) => file.endsWith(".webm"));
if (webm) {
  const source = path.join(outputDir, webm);
  const target = path.join(repoRoot, "outputs", "MedArchive_demo_video.webm");
  await fs.copyFile(source, target);
  console.log(target);
} else {
  throw new Error("Playwright did not produce a .webm recording.");
}
