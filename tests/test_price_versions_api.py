from __future__ import annotations

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.price_versions import get_price_version_repository

from tests.fakes import FakePriceVersionRepository


def test_price_versions_api_lists_published_versions_by_default() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get("/api/v1/price-versions", headers={"X-API-Key": "dev-integration"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["verification_status"] == "published"
    assert body[0]["external_partner_id"] == "clinic-001"
    assert body[0]["external_service_id"] == "svc-001"
    assert repository.filters["verification_status"] == "published"
    assert repository.filters["limit"] == 50


def test_price_versions_api_passes_filters_to_repository() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/price-versions?status=superseded&limit=10&offset=0",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert repository.filters["verification_status"] == "superseded"
    assert repository.filters["limit"] == 10


def test_service_offers_api_filters_by_external_service_id() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/services/svc-001/offers",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert repository.filters["verification_status"] == "published"
    assert repository.filters["external_service_id"] == "svc-001"


def test_partner_prices_api_filters_by_external_partner_id() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/partners/clinic-001/prices",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert repository.filters["verification_status"] == "published"
    assert repository.filters["external_partner_id"] == "clinic-001"


def test_price_changes_api_requires_changed_since_cursor() -> None:
    repository = FakePriceVersionRepository()
    app = create_app()
    app.dependency_overrides[get_price_version_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/price-changes?changed_since=2026-06-26T00:00:00Z",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert repository.filters["verification_status"] == "published"
    assert repository.filters["changed_since"] is not None
