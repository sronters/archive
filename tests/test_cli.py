from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from medarchive_infrastructure import cli


def test_ingest_cli_uploads_supported_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = tmp_path / "price.xlsx"
    document.write_bytes(b"test")
    captured: dict[str, Any] = {}

    def fake_upload_files(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"status": "processed", "document_count": 1}

    monkeypatch.setattr(cli, "_upload_files", fake_upload_files)

    cli.main(
        [
            "ingest",
            str(document),
            "--api-url",
            "https://med.example",
            "--idempotency-key",
            "demo-1",
        ]
    )

    assert captured["paths"] == [document]
    assert captured["api_url"] == "https://med.example"
    assert captured["idempotency_key"] == "demo-1"
    assert json.loads(capsys.readouterr().out)["status"] == "processed"


def test_upload_paths_rejects_directory_without_supported_files(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="ZIP, PDF, DOCX, XLS или XLSX"):
        cli._upload_paths(tmp_path)
