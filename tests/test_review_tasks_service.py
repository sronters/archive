from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from medarchive_application.review_tasks import (
    CorrectReviewTaskCommand,
    ReviewTaskService,
    ReviewTaskSummary,
)

from tests.fakes import FakeReviewTaskRepository


def test_correct_review_task_requires_at_least_one_price() -> None:
    task_id = uuid4()
    service = ReviewTaskService(
        repository=FakeReviewTaskRepository(
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
    )

    with pytest.raises(ValueError, match="At least one corrected price is required"):
        service.correct_task(
            task_id=task_id,
            command=CorrectReviewTaskCommand(
                operator_id=uuid4(),
                service_id=uuid4(),
                resident_price_kzt=None,
                nonresident_price_kzt=None,
            ),
        )


def test_correct_review_task_accepts_decimal_price() -> None:
    task_id = uuid4()
    service = ReviewTaskService(
        repository=FakeReviewTaskRepository(
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
    )

    result = service.correct_task(
        task_id=task_id,
        command=CorrectReviewTaskCommand(
            operator_id=uuid4(),
            service_id=uuid4(),
            resident_price_kzt=Decimal("25000"),
            nonresident_price_kzt=None,
        ),
    )

    assert result.task.status == "corrected"
    assert result.price_version_id is not None
