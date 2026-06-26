from __future__ import annotations

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.exports import get_price_version_repository

from tests.fakes import FakePriceVersionRepository


def test_exports_api_returns_json_attachment() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/exports/price-versions?format=json",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="price-versions.json"'
    assert response.json()[0]["external_partner_id"] == "clinic-001"


def test_exports_api_returns_csv_attachment_with_filters() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/exports/price-versions?format=csv&external_service_id=svc-001",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="price-versions.csv"'
    assert "clinic-001" in response.content.decode("utf-8-sig")
    assert repository.filters["external_service_id"] == "svc-001"
