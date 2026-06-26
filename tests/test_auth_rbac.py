from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from medarchive_api.config import Settings, get_settings
from medarchive_api.main import create_app
from medarchive_api.routers.catalog_import import get_catalog_import_repository
from medarchive_api.routers.ingestion import get_ingestion_recorder
from medarchive_api.routers.search import get_search_repository

from tests.fakes import FakeCatalogImportRepository, FakeIngestionRecorder, FakeSearchRepository
from tests.fixtures_xlsx import build_xlsx


def test_ingestion_requires_api_key(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(local_storage_root=str(tmp_path))
    app.dependency_overrides[get_ingestion_recorder] = FakeIngestionRecorder
    client = TestClient(app)

    response = client.post(
        "/api/v1/ingestion-batches",
        files={
            "files": (
                "price.xlsx",
                build_xlsx([["service", "price"], ["MRI", "1000"]]),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing X-API-Key header."


def test_integration_client_cannot_import_catalog() -> None:
    app = create_app()
    app.dependency_overrides[get_catalog_import_repository] = FakeCatalogImportRepository
    client = TestClient(app)
    payload = json.dumps(
        [{"external_service_id": "svc-001", "official_name": "MRI brain"}],
    ).encode()

    response = client.post(
        "/api/v1/service-catalog/imports",
        files={"file": ("services.json", payload, "application/json")},
        data={"mode": "apply"},
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 403


def test_catalog_manager_can_import_catalog() -> None:
    repository = FakeCatalogImportRepository()
    app = create_app()
    app.dependency_overrides[get_catalog_import_repository] = lambda: repository
    client = TestClient(app)
    payload = json.dumps(
        [{"external_service_id": "svc-001", "official_name": "MRI brain"}],
    ).encode()

    response = client.post(
        "/api/v1/service-catalog/imports",
        files={"file": ("services.json", payload, "application/json")},
        data={"mode": "apply"},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    assert repository.applied_services[0].external_service_id == "svc-001"


def test_oidc_bearer_token_mode_authorizes_admin() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(auth_mode="oidc")
    app.dependency_overrides[get_search_repository] = FakeSearchRepository
    client = TestClient(app)

    response = client.get(
        "/api/v1/services/search?q=MRI",
        headers={"Authorization": "Bearer dev-oidc-admin"},
    )

    assert response.status_code == 200


def test_trusted_reverse_proxy_mode_uses_forwarded_identity() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(auth_mode="trusted_reverse_proxy")
    app.dependency_overrides[get_search_repository] = FakeSearchRepository
    client = TestClient(app)

    response = client.get(
        "/api/v1/services/search?q=MRI",
        headers={
            "X-Forwarded-User": "operator-1",
            "X-Forwarded-Roles": "viewer",
        },
    )

    assert response.status_code == 200
