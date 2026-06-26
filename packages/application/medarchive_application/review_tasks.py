from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


class ReviewTaskConflictError(Exception):
    """Raised when a review task was already claimed or changed by another operator."""


@dataclass(frozen=True)
class ReviewTaskSummary:
    task_id: UUID
    extracted_item_id: UUID
    reason: str
    priority: int
    status: str
    assigned_to: UUID | None
    version: int


@dataclass(frozen=True)
class CorrectReviewTaskCommand:
    operator_id: UUID
    service_id: UUID
    resident_price_kzt: Decimal | None
    nonresident_price_kzt: Decimal | None


@dataclass(frozen=True)
class ReviewDecisionResult:
    task: ReviewTaskSummary
    price_version_id: UUID | None
    audit_event_id: UUID


class ReviewTaskRepository(Protocol):
    def list_tasks(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[ReviewTaskSummary, ...]:
        ...

    def claim_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewTaskSummary:
        ...

    def approve_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        ...

    def reject_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        reason: str,
    ) -> ReviewDecisionResult:
        ...

    def correct_task(
        self,
        *,
        task_id: UUID,
        command: CorrectReviewTaskCommand,
    ) -> ReviewDecisionResult:
        ...

    def release_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        ...


class ReviewTaskService:
    def __init__(self, *, repository: ReviewTaskRepository) -> None:
        self._repository = repository

    def list_tasks(
        self,
        *,
        status: str | None = "open",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[ReviewTaskSummary, ...]:
        bounded_limit = min(max(limit, 1), 200)
        bounded_offset = max(offset, 0)
        return self._repository.list_tasks(
            status=status,
            limit=bounded_limit,
            offset=bounded_offset,
        )

    def claim_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewTaskSummary:
        return self._repository.claim_task(task_id=task_id, operator_id=operator_id)

    def approve_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        return self._repository.approve_task(task_id=task_id, operator_id=operator_id)

    def reject_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        reason: str,
    ) -> ReviewDecisionResult:
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("Reject reason is required.")
        return self._repository.reject_task(
            task_id=task_id,
            operator_id=operator_id,
            reason=clean_reason,
        )

    def correct_task(
        self,
        *,
        task_id: UUID,
        command: CorrectReviewTaskCommand,
    ) -> ReviewDecisionResult:
        if command.resident_price_kzt is None and command.nonresident_price_kzt is None:
            raise ValueError("At least one corrected price is required.")
        return self._repository.correct_task(task_id=task_id, command=command)

    def release_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        return self._repository.release_task(task_id=task_id, operator_id=operator_id)
