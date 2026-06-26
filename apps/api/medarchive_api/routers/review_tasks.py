from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from medarchive_application.review_tasks import (
    CorrectReviewTaskCommand,
    ReviewDecisionResult,
    ReviewTaskConflictError,
    ReviewTaskRepository,
    ReviewTaskService,
    ReviewTaskSummary,
)
from medarchive_infrastructure.review import SqlAlchemyReviewTaskRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class ReviewTaskResponse(BaseModel):
    task_id: UUID
    extracted_item_id: UUID
    reason: str
    priority: int
    status: str
    assigned_to: UUID | None
    version: int


class ClaimReviewTaskRequest(BaseModel):
    operator_id: UUID = Field(description="Operator identity from the configured identity adapter.")


class RejectReviewTaskRequest(BaseModel):
    operator_id: UUID = Field(description="Operator identity from the configured identity adapter.")
    reason: str = Field(min_length=1, max_length=1024)


class CorrectReviewTaskRequest(BaseModel):
    operator_id: UUID = Field(description="Operator identity from the configured identity adapter.")
    service_id: UUID
    resident_price_kzt: Decimal | None = Field(default=None, ge=0)
    nonresident_price_kzt: Decimal | None = Field(default=None, ge=0)


class ReviewDecisionResponse(BaseModel):
    task: ReviewTaskResponse
    price_version_id: UUID | None
    audit_event_id: UUID


router = APIRouter(prefix="/review-tasks", tags=["review-tasks"])


@router.get("", response_model=list[ReviewTaskResponse])
def list_review_tasks(
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator", "auditor")),
    ],
    task_status: Annotated[str | None, Query(alias="status")] = "open",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReviewTaskResponse]:
    service = ReviewTaskService(repository=repository)
    tasks = service.list_tasks(status=task_status, limit=limit, offset=offset)
    return [_response(task) for task in tasks]


@router.post("/{task_id}/claim", response_model=ReviewTaskResponse)
def claim_review_task(
    task_id: UUID,
    payload: ClaimReviewTaskRequest,
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
) -> ReviewTaskResponse:
    service = ReviewTaskService(repository=repository)
    try:
        task = service.claim_task(task_id=task_id, operator_id=payload.operator_id)
    except ReviewTaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _response(task)


@router.post("/{task_id}/approve", response_model=ReviewDecisionResponse)
def approve_review_task(
    task_id: UUID,
    payload: ClaimReviewTaskRequest,
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
) -> ReviewDecisionResponse:
    service = ReviewTaskService(repository=repository)
    try:
        result = service.approve_task(task_id=task_id, operator_id=payload.operator_id)
    except ReviewTaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _decision_response(result)


@router.post("/{task_id}/reject", response_model=ReviewDecisionResponse)
def reject_review_task(
    task_id: UUID,
    payload: RejectReviewTaskRequest,
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
) -> ReviewDecisionResponse:
    service = ReviewTaskService(repository=repository)
    try:
        result = service.reject_task(
            task_id=task_id,
            operator_id=payload.operator_id,
            reason=payload.reason,
        )
    except ReviewTaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _decision_response(result)


@router.post("/{task_id}/correct", response_model=ReviewDecisionResponse)
def correct_review_task(
    task_id: UUID,
    payload: CorrectReviewTaskRequest,
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
) -> ReviewDecisionResponse:
    service = ReviewTaskService(repository=repository)
    try:
        result = service.correct_task(
            task_id=task_id,
            command=CorrectReviewTaskCommand(
                operator_id=payload.operator_id,
                service_id=payload.service_id,
                resident_price_kzt=payload.resident_price_kzt,
                nonresident_price_kzt=payload.nonresident_price_kzt,
            ),
        )
    except ReviewTaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _decision_response(result)


@router.post("/{task_id}/release", response_model=ReviewDecisionResponse)
def release_review_task(
    task_id: UUID,
    payload: ClaimReviewTaskRequest,
    repository: Annotated[ReviewTaskRepository, Depends(get_review_task_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
) -> ReviewDecisionResponse:
    service = ReviewTaskService(repository=repository)
    try:
        result = service.release_task(task_id=task_id, operator_id=payload.operator_id)
    except ReviewTaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _decision_response(result)


def get_review_task_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReviewTaskRepository:
    return SqlAlchemyReviewTaskRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _response(task: ReviewTaskSummary) -> ReviewTaskResponse:
    return ReviewTaskResponse(
        task_id=task.task_id,
        extracted_item_id=task.extracted_item_id,
        reason=task.reason,
        priority=task.priority,
        status=task.status,
        assigned_to=task.assigned_to,
        version=task.version,
    )


def _decision_response(result: ReviewDecisionResult) -> ReviewDecisionResponse:
    return ReviewDecisionResponse(
        task=_response(result.task),
        price_version_id=result.price_version_id,
        audit_event_id=result.audit_event_id,
    )
