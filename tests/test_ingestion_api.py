from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from medarchive_api.config import Settings, get_settings
from medarchive_api.main import create_app
from medarchive_api.routers.ingestion import get_ingestion_recorder

from tests.fakes import FakeIngestionRecorder
from tests.fixtures_xlsx import build_xlsx


def test_create_ingestion_batch_returns_202_and_contract_shape(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(local_storage_root=str(tmp_path))
    app.dependency_overrides[get_ingestion_recorder] = FakeIngestionRecorder
    client = TestClient(app)
    workbook = build_xlsx([["Название услуги", "Цена"], ["МРТ", "1000"]])

    response = client.post(
        "/api/v1/ingestion-batches",
        files=[
            (
                "files",
                (
                    "price.xlsx",
                    workbook,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
        headers={"Idempotency-Key": "contract-test", "X-API-Key": "dev-admin"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["accepted_documents_count"] == 1
    assert body["rejected_documents_count"] == 0
    assert body["links"]["self"].startswith("/api/v1/ingestion-batches/")
    assert body["links"]["documents"].startswith("/api/v1/documents?batch_id=")
