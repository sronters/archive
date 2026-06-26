from __future__ import annotations

from fastapi.testclient import TestClient
from medarchive_api.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {"status": "ok", "service": "medarchive-api"}


def test_system_status_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["api_namespace"] == "/api/v1"


def test_metrics_endpoint_exposes_prometheus_text() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert "medarchive_api_info" in response.text
    assert "medarchive_http_requests_total" in response.text
    assert "medarchive_http_request_duration_seconds_bucket" in response.text
    assert response.headers["content-type"].startswith("text/plain")
