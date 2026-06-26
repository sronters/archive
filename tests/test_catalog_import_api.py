from __future__ import annotations

import json

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.catalog_import import get_catalog_import_repository

from tests.fakes import FakeCatalogImportRepository


def test_service_catalog_import_preview_returns_report_without_apply() -> None:
    repository = FakeCatalogImportRepository()
    app = create_app()
    app.dependency_overrides[get_catalog_import_repository] = lambda: repository
    client = TestClient(app)
    payload = json.dumps(
        [
            {
                "external_service_id": "svc-001",
                "official_name": "MRI brain",
                "synonyms": ["Magnetic resonance brain"],
                "category": "diagnostics",
                "is_active": True,
            }
        ]
    ).encode()

    response = client.post(
        "/api/v1/service-catalog/imports",
        files={"file": ("services.json", payload, "application/json")},
        data={"mode": "preview"},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["entity_type"] == "service"
    assert body["created_count"] == 1
    assert repository.applied_services == ()


def test_partner_import_apply_upserts_records() -> None:
    repository = FakeCatalogImportRepository()
    app = create_app()
    app.dependency_overrides[get_catalog_import_repository] = lambda: repository
    client = TestClient(app)
    payload = json.dumps(
        [
            {
                "external_partner_id": "clinic-001",
                "name": "Medical Center",
                "bin": "123456789012",
                "city": "Astana",
                "is_active": True,
            }
        ]
    ).encode()

    response = client.post(
        "/api/v1/partners/imports",
        files={"file": ("partners.json", payload, "application/json")},
        data={"mode": "apply"},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["entity_type"] == "partner"
    assert body["created_count"] == 1
    assert repository.applied_partners[0].external_partner_id == "clinic-001"


def test_service_catalog_apply_reports_duplicate_external_id() -> None:
    repository = FakeCatalogImportRepository()
    app = create_app()
    app.dependency_overrides[get_catalog_import_repository] = lambda: repository
    client = TestClient(app)
    payload = json.dumps(
        [
            {"external_service_id": "svc-001", "official_name": "MRI brain"},
            {"external_service_id": "svc-001", "official_name": "MRI duplicate"},
        ]
    ).encode()

    response = client.post(
        "/api/v1/service-catalog/imports",
        files={"file": ("services.json", payload, "application/json")},
        data={"mode": "apply"},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["issues"][0]["code"] == "duplicate_external_service_id"
    assert repository.applied_services == ()
