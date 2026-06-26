from __future__ import annotations

from pathlib import Path


def test_quality_and_runbook_docs_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "docs/runbooks/failed-document-processing.md",
        root / "docs/runbooks/queue-backlog.md",
        root / "docs/runbooks/webhook-delivery-failures.md",
        root / "docs/quality/golden-dataset.md",
        root / "docs/quality/test-gates.md",
    ]

    for path in required:
        assert path.exists(), f"missing {path}"
        assert path.read_text(encoding="utf-8").strip()


def test_golden_dataset_manifest_tracks_primary_ocr_metric() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = (root / "docs/quality/golden-dataset.md").read_text(encoding="utf-8")

    assert "price_exact_match" in manifest
    assert "Scanned PDF" in manifest
    assert "XLS legacy workbook" in manifest
