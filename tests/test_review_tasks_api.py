from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.review_tasks import get_review_task_repository
from medarchive_application.review_tasks import ReviewTaskSummary

from tests.fakes import FakeReviewTaskRepository


def test_review_tasks_api_lists_and_claims_tasks() -> None:
    task_id = uuid4()
    extracted_item_id = uuid4()
    operator_id = uuid4()
    repository = FakeReviewTaskRepository(
        (
            ReviewTaskSummary(
                task_id=task_id,
                extracted_item_id=extracted_item_id,
                reason="service_match_uncertain",
                priority=60,
                status="open",
                assigned_to=None,
                version=0,
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_review_task_repository] = lambda: repository
    client = TestClient(app)

    list_response = client.get("/api/v1/review-tasks", headers={"X-API-Key": "dev-admin"})

    assert list_response.status_code == 200
    assert list_response.json()[0]["task_id"] == str(task_id)

    claim_response = client.post(
        f"/api/v1/review-tasks/{task_id}/claim",
        json={"operator_id": str(operator_id)},
        headers={"X-API-Key": "dev-admin"},
    )

    assert claim_response.status_code == 200
    body = claim_response.json()
    assert body["status"] == "claimed"
    assert body["assigned_to"] == str(operator_id)
    assert body["version"] == 1


def test_review_tasks_api_returns_conflict_for_already_claimed_task() -> None:
    task_id = uuid4()
    repository = FakeReviewTaskRepository(
        (
            ReviewTaskSummary(
                task_id=task_id,
                extracted_item_id=uuid4(),
                reason="partner_unresolved",
                priority=80,
                status="claimed",
                assigned_to=uuid4(),
                version=3,
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_review_task_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        f"/api/v1/review-tasks/{task_id}/claim",
        json={"operator_id": str(uuid4())},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 409


def test_review_tasks_api_approves_task_and_returns_publication_metadata() -> None:
    task_id = uuid4()
    operator_id = uuid4()
    repository = FakeReviewTaskRepository(
        (
            ReviewTaskSummary(
                task_id=task_id,
                extracted_item_id=uuid4(),
                reason="service_match_uncertain",
                priority=60,
                status="claimed",
                assigned_to=operator_id,
                version=1,
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_review_task_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        f"/api/v1/review-tasks/{task_id}/approve",
        json={"operator_id": str(operator_id)},
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["status"] == "approved"
    assert body["price_version_id"] is not None
    assert body["audit_event_id"] is not None


def test_review_tasks_api_corrects_task_and_publishes_corrected_price() -> None:
    task_id = uuid4()
    operator_id = uuid4()
    service_id = uuid4()
    repository = FakeReviewTaskRepository(
        (
            ReviewTaskSummary(
                task_id=task_id,
                extracted_item_id=uuid4(),
                reason="missing_price",
                priority=80,
                status="open",
                assigned_to=None,
                version=0,
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_review_task_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        f"/api/v1/review-tasks/{task_id}/correct",
        json={
            "operator_id": str(operator_id),
            "service_id": str(service_id),
            "resident_price_kzt": "25000",
            "nonresident_price_kzt": "32000",
        },
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["status"] == "corrected"
    assert body["price_version_id"] is not None


def test_review_tasks_api_rejects_and_releases_tasks() -> None:
    claimed_task_id = uuid4()
    rejected_task_id = uuid4()
    operator_id = uuid4()
    repository = FakeReviewTaskRepository(
        (
            ReviewTaskSummary(
                task_id=claimed_task_id,
                extracted_item_id=uuid4(),
                reason="partner_unresolved",
                priority=80,
                status="claimed",
                assigned_to=operator_id,
                version=2,
            ),
            ReviewTaskSummary(
                task_id=rejected_task_id,
                extracted_item_id=uuid4(),
                reason="service_match_uncertain",
                priority=60,
                status="open",
                assigned_to=None,
                version=0,
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_review_task_repository] = lambda: repository
    client = TestClient(app)

    release_response = client.post(
        f"/api/v1/review-tasks/{claimed_task_id}/release",
        json={"operator_id": str(operator_id)},
        headers={"X-API-Key": "dev-admin"},
    )
    reject_response = client.post(
        f"/api/v1/review-tasks/{rejected_task_id}/reject",
        json={"operator_id": str(operator_id), "reason": "Not a medical service row."},
        headers={"X-API-Key": "dev-admin"},
    )

    assert release_response.status_code == 200
    assert release_response.json()["task"]["status"] == "open"
    assert reject_response.status_code == 200
    assert reject_response.json()["task"]["status"] == "rejected"
