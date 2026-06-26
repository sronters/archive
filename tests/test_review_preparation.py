from __future__ import annotations

from uuid import uuid4

from medarchive_application.review_preparation import (
    ExtractedItemForReview,
    ReviewDocumentContext,
    ReviewPreparationService,
)
from medarchive_matching.simple_matcher import CatalogService

from tests.fakes import FakeReviewPreparationRepository


def test_review_preparation_persists_matches_and_review_tasks() -> None:
    service_id = uuid4()
    extracted_item_id = uuid4()
    repository = FakeReviewPreparationRepository(
        context=ReviewDocumentContext(document_id=uuid4(), partner_id=None),
        items=(
            ExtractedItemForReview(
                extracted_item_id=extracted_item_id,
                service_name_raw="Unknown service",
                resident_price_raw="25000",
                nonresident_price_raw="32000",
            ),
        ),
        catalog=(
            CatalogService(
                service_id=service_id,
                official_name="MRI brain",
                external_service_id="srv-1",
            ),
        ),
    )
    service = ReviewPreparationService(repository=repository)

    result = service.prepare_run(uuid4())

    assert result.document_status == "NEEDS_REVIEW"
    assert result.review_task_count == 1
    assert repository.saved_matches[0].service_id == service_id
    assert repository.saved_tasks[0].extracted_item_id == extracted_item_id
    assert "service_match_uncertain" in repository.saved_tasks[0].reason
    assert "partner_unresolved" in repository.saved_tasks[0].reason


def test_review_preparation_marks_document_verified_when_row_is_precise() -> None:
    service_id = uuid4()
    repository = FakeReviewPreparationRepository(
        context=ReviewDocumentContext(document_id=uuid4(), partner_id=uuid4()),
        items=(
            ExtractedItemForReview(
                extracted_item_id=uuid4(),
                service_name_raw="MRI brain",
                resident_price_raw="25000",
                nonresident_price_raw="32000",
            ),
        ),
        catalog=(CatalogService(service_id=service_id, official_name="MRI brain"),),
    )
    service = ReviewPreparationService(repository=repository)

    result = service.prepare_run(uuid4())

    assert result.document_status == "VERIFIED"
    assert result.review_task_count == 0
    assert repository.saved_tasks == ()
    assert repository.saved_matches[0].service_id == service_id
