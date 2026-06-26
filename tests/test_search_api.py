from __future__ import annotations

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.search import get_search_repository

from tests.fakes import FakeSearchRepository


def test_service_search_filters_and_requires_auth() -> None:
    repository = FakeSearchRepository()
    app = create_app()
    app.dependency_overrides[get_search_repository] = lambda: repository
    client = TestClient(app)

    unauthorized = client.get("/api/v1/services/search?q=MRI")
    response = client.get(
        "/api/v1/services/search?q=MRI&category=diagnostics&limit=10",
        headers={"X-API-Key": "dev-integration"},
    )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()[0]["external_service_id"] == "svc-001"
    assert repository.service_filters["query"] == "MRI"
    assert repository.service_filters["category"] == "diagnostics"
    assert repository.service_filters["limit"] == 10


def test_partner_search_filters() -> None:
    repository = FakeSearchRepository()
    app = create_app()
    app.dependency_overrides[get_search_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        "/api/v1/partners/search?q=Medical&city=Astana",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 200
    assert response.json()[0]["external_partner_id"] == "clinic-001"
    assert repository.partner_filters["query"] == "Medical"
    assert repository.partner_filters["city"] == "Astana"
