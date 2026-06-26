from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from medarchive_application.graph_projection import PRICE_VERSION_PUBLISHED
from medarchive_application.review_preparation import (
    ExtractedItemForReview,
    ReviewDocumentContext,
    ReviewTaskDraft,
    ServiceMatchDraft,
)
from medarchive_application.review_tasks import (
    CorrectReviewTaskCommand,
    ReviewDecisionResult,
    ReviewTaskConflictError,
    ReviewTaskSummary,
)
from medarchive_document_parsers.xlsx import parse_kzt_price
from medarchive_matching.simple_matcher import CatalogService
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    AuditEventModel,
    ExtractedPriceItemModel,
    OutboxEventModel,
    PriceDocumentModel,
    PriceVersionModel,
    ProcessingRunModel,
    ReviewTaskModel,
    ServiceMatchModel,
    ServiceModel,
)


class SqlAlchemyReviewPreparationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_document_context(self, processing_run_id: UUID) -> ReviewDocumentContext:
        with self._session_factory() as session:
            statement = (
                select(PriceDocumentModel.id, PriceDocumentModel.partner_id)
                .join(ProcessingRunModel, ProcessingRunModel.document_id == PriceDocumentModel.id)
                .where(ProcessingRunModel.id == processing_run_id)
            )
            row = session.execute(statement).one()
            return ReviewDocumentContext(document_id=row.id, partner_id=row.partner_id)

    def list_extracted_items(self, processing_run_id: UUID) -> tuple[ExtractedItemForReview, ...]:
        with self._session_factory() as session:
            statement = (
                select(ExtractedPriceItemModel)
                .where(ExtractedPriceItemModel.processing_run_id == processing_run_id)
                .order_by(ExtractedPriceItemModel.sheet_name, ExtractedPriceItemModel.row_number)
            )
            return tuple(
                ExtractedItemForReview(
                    extracted_item_id=row.id,
                    service_name_raw=row.service_name_raw,
                    resident_price_raw=row.resident_price_raw,
                    nonresident_price_raw=row.nonresident_price_raw,
                )
                for row in session.execute(statement).scalars()
            )

    def list_catalog_services(self) -> tuple[CatalogService, ...]:
        with self._session_factory() as session:
            statement = select(ServiceModel).where(ServiceModel.is_active.is_(True))
            return tuple(
                CatalogService(
                    service_id=row.id,
                    official_name=row.official_name,
                    external_service_id=row.external_service_id,
                    synonyms=tuple(row.synonyms or ()),
                    category=row.category,
                )
                for row in session.execute(statement).scalars()
            )

    def has_review_output(self, processing_run_id: UUID) -> bool:
        with self._session_factory() as session:
            match_count = session.scalar(
                select(func.count(ServiceMatchModel.id))
                .join(
                    ExtractedPriceItemModel,
                    ExtractedPriceItemModel.id == ServiceMatchModel.extracted_item_id,
                )
                .where(ExtractedPriceItemModel.processing_run_id == processing_run_id)
            )
            task_count = session.scalar(
                select(func.count(ReviewTaskModel.id))
                .join(
                    ExtractedPriceItemModel,
                    ExtractedPriceItemModel.id == ReviewTaskModel.extracted_item_id,
                )
                .where(ExtractedPriceItemModel.processing_run_id == processing_run_id)
            )
            return bool(match_count or task_count)

    def save_review_output(
        self,
        *,
        processing_run_id: UUID,
        service_matches: tuple[ServiceMatchDraft, ...],
        review_tasks: tuple[ReviewTaskDraft, ...],
        matcher_version: str,
        document_status: str,
    ) -> None:
        with self._session_factory() as session:
            run = session.get(ProcessingRunModel, processing_run_id)
            if run is None:
                raise ValueError(f"Processing run does not exist: {processing_run_id}")
            session.add_all(
                ServiceMatchModel(
                    extracted_item_id=match.extracted_item_id,
                    service_id=match.service_id,
                    retrieval_method=match.retrieval_method,
                    retrieval_score=match.retrieval_score,
                    reranker_score=match.reranker_score,
                    matcher_version=match.matcher_version,
                    rank=match.rank,
                )
                for match in service_matches
            )
            session.add_all(
                ReviewTaskModel(
                    extracted_item_id=task.extracted_item_id,
                    reason=task.reason,
                    priority=task.priority,
                    status="open",
                )
                for task in review_tasks
            )
            run.matcher_version = matcher_version
            run.status = "review_prepared"
            run.finished_at = datetime.now(timezone.utc)  # noqa: UP017
            document = session.get(PriceDocumentModel, run.document_id)
            if document is None:
                raise ValueError(f"Price document does not exist: {run.document_id}")
            document.status = document_status
            session.commit()


class SqlAlchemyReviewTaskRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_tasks(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[ReviewTaskSummary, ...]:
        with self._session_factory() as session:
            statement = select(ReviewTaskModel).order_by(
                ReviewTaskModel.priority.desc(),
                ReviewTaskModel.created_at.asc(),
            )
            if status is not None:
                statement = statement.where(ReviewTaskModel.status == status)
            rows = session.execute(statement.limit(limit).offset(offset)).scalars()
            return tuple(_review_task_summary(row) for row in rows)

    def claim_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewTaskSummary:
        with self._session_factory() as session:
            task = session.get(ReviewTaskModel, task_id)
            if task is None:
                raise ValueError(f"Review task does not exist: {task_id}")
            if task.assigned_to is not None and task.assigned_to != operator_id:
                raise ReviewTaskConflictError("Review task is already assigned.")
            if task.status not in {"open", "claimed"}:
                raise ReviewTaskConflictError(f"Review task cannot be claimed from {task.status}.")
            task.assigned_to = operator_id
            task.status = "claimed"
            task.version += 1
            session.commit()
            return _review_task_summary(task)

    def approve_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        with self._session_factory() as session:
            context = _load_review_context(session, task_id)
            _ensure_operator_can_decide(context.task, operator_id)
            service_id = _best_service_id(session, context.extracted_item.id)
            if service_id is None:
                raise ReviewTaskConflictError("Review task has no service match to approve.")
            resident_price = parse_kzt_price(context.extracted_item.resident_price_raw)
            nonresident_price = parse_kzt_price(context.extracted_item.nonresident_price_raw)
            price_version_id = _publish_price_version(
                session,
                context=context,
                service_id=service_id,
                resident_price=resident_price,
                nonresident_price=nonresident_price,
            )
            before = _review_task_state(context.task)
            context.task.status = "approved"
            context.task.assigned_to = operator_id
            context.task.version += 1
            audit_event = _audit_review_decision(
                session,
                actor_id=operator_id,
                action="review_task.approved",
                task=context.task,
                before=before,
                after={
                    **_review_task_state(context.task),
                    "price_version_id": str(price_version_id),
                    "service_id": str(service_id),
                },
            )
            session.commit()
            return ReviewDecisionResult(
                task=_review_task_summary(context.task),
                price_version_id=price_version_id,
                audit_event_id=audit_event.id,
            )

    def reject_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        reason: str,
    ) -> ReviewDecisionResult:
        with self._session_factory() as session:
            context = _load_review_context(session, task_id)
            _ensure_operator_can_decide(context.task, operator_id)
            before = _review_task_state(context.task)
            context.task.status = "rejected"
            context.task.assigned_to = operator_id
            context.task.version += 1
            audit_event = _audit_review_decision(
                session,
                actor_id=operator_id,
                action="review_task.rejected",
                task=context.task,
                before=before,
                after={**_review_task_state(context.task), "reject_reason": reason},
            )
            session.commit()
            return ReviewDecisionResult(
                task=_review_task_summary(context.task),
                price_version_id=None,
                audit_event_id=audit_event.id,
            )

    def correct_task(
        self,
        *,
        task_id: UUID,
        command: CorrectReviewTaskCommand,
    ) -> ReviewDecisionResult:
        with self._session_factory() as session:
            context = _load_review_context(session, task_id)
            _ensure_operator_can_decide(context.task, command.operator_id)
            price_version_id = _publish_price_version(
                session,
                context=context,
                service_id=command.service_id,
                resident_price=command.resident_price_kzt,
                nonresident_price=command.nonresident_price_kzt,
            )
            before = _review_task_state(context.task)
            context.task.status = "corrected"
            context.task.assigned_to = command.operator_id
            context.task.version += 1
            audit_event = _audit_review_decision(
                session,
                actor_id=command.operator_id,
                action="review_task.corrected",
                task=context.task,
                before=before,
                after={
                    **_review_task_state(context.task),
                    "price_version_id": str(price_version_id),
                    "service_id": str(command.service_id),
                    "resident_price_kzt": _decimal_string(command.resident_price_kzt),
                    "nonresident_price_kzt": _decimal_string(command.nonresident_price_kzt),
                },
            )
            session.commit()
            return ReviewDecisionResult(
                task=_review_task_summary(context.task),
                price_version_id=price_version_id,
                audit_event_id=audit_event.id,
            )

    def release_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        with self._session_factory() as session:
            task = session.get(ReviewTaskModel, task_id)
            if task is None:
                raise ValueError(f"Review task does not exist: {task_id}")
            if task.assigned_to is not None and task.assigned_to != operator_id:
                raise ReviewTaskConflictError("Review task is assigned to another operator.")
            if task.status != "claimed":
                raise ReviewTaskConflictError(f"Review task cannot be released from {task.status}.")
            before = _review_task_state(task)
            task.status = "open"
            task.assigned_to = None
            task.version += 1
            audit_event = _audit_review_decision(
                session,
                actor_id=operator_id,
                action="review_task.released",
                task=task,
                before=before,
                after=_review_task_state(task),
            )
            session.commit()
            return ReviewDecisionResult(
                task=_review_task_summary(task),
                price_version_id=None,
                audit_event_id=audit_event.id,
            )


def _review_task_summary(row: ReviewTaskModel) -> ReviewTaskSummary:
    return ReviewTaskSummary(
        task_id=row.id,
        extracted_item_id=row.extracted_item_id,
        reason=row.reason,
        priority=row.priority,
        status=row.status,
        assigned_to=row.assigned_to,
        version=row.version,
    )


@dataclass(frozen=True)
class _ReviewContext:
    task: ReviewTaskModel
    extracted_item: ExtractedPriceItemModel
    processing_run: ProcessingRunModel
    document: PriceDocumentModel


def _load_review_context(session: Session, task_id: UUID) -> _ReviewContext:
    statement = (
        select(
            ReviewTaskModel,
            ExtractedPriceItemModel,
            ProcessingRunModel,
            PriceDocumentModel,
        )
        .join(
            ExtractedPriceItemModel,
            ExtractedPriceItemModel.id == ReviewTaskModel.extracted_item_id,
        )
        .join(
            ProcessingRunModel,
            ProcessingRunModel.id == ExtractedPriceItemModel.processing_run_id,
        )
        .join(PriceDocumentModel, PriceDocumentModel.id == ProcessingRunModel.document_id)
        .where(ReviewTaskModel.id == task_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise ValueError(f"Review task does not exist: {task_id}")
    task, extracted_item, processing_run, document = row
    return _ReviewContext(
        task=task,
        extracted_item=extracted_item,
        processing_run=processing_run,
        document=document,
    )


def _ensure_operator_can_decide(task: ReviewTaskModel, operator_id: UUID) -> None:
    if task.status not in {"open", "claimed"}:
        raise ReviewTaskConflictError(f"Review task cannot be decided from {task.status}.")
    if task.assigned_to is not None and task.assigned_to != operator_id:
        raise ReviewTaskConflictError("Review task is assigned to another operator.")


def _best_service_id(session: Session, extracted_item_id: UUID) -> UUID | None:
    statement = (
        select(ServiceMatchModel.service_id)
        .where(ServiceMatchModel.extracted_item_id == extracted_item_id)
        .order_by(ServiceMatchModel.rank.asc())
        .limit(1)
    )
    return session.execute(statement).scalar_one_or_none()


def _publish_price_version(
    session: Session,
    *,
    context: _ReviewContext,
    service_id: UUID,
    resident_price: Decimal | None,
    nonresident_price: Decimal | None,
) -> UUID:
    if context.document.partner_id is None:
        raise ReviewTaskConflictError("Cannot publish price without resolved partner.")
    if resident_price is None and nonresident_price is None:
        raise ReviewTaskConflictError("Cannot publish price without numeric price values.")

    effective_date = context.document.effective_date or date.today()
    existing = session.execute(
        select(PriceVersionModel)
        .where(PriceVersionModel.source_document_id == context.document.id)
        .where(PriceVersionModel.service_id == service_id)
        .where(PriceVersionModel.verification_status == "published")
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id

    current_versions = session.execute(
        select(PriceVersionModel)
        .where(PriceVersionModel.partner_id == context.document.partner_id)
        .where(PriceVersionModel.service_id == service_id)
        .where(PriceVersionModel.valid_to.is_(None))
        .where(PriceVersionModel.verification_status == "published")
    ).scalars()
    for current in current_versions:
        current.valid_to = effective_date
        current.verification_status = "superseded"

    published = PriceVersionModel(
        partner_id=context.document.partner_id,
        service_id=service_id,
        source_document_id=context.document.id,
        resident_price_kzt=resident_price,
        nonresident_price_kzt=nonresident_price,
        original_price=resident_price or nonresident_price,
        original_currency="KZT",
        exchange_rate=Decimal("1"),
        valid_from=effective_date,
        valid_to=None,
        published_at=datetime.now(timezone.utc),  # noqa: UP017
        verification_status="published",
    )
    session.add(published)
    session.flush()
    session.add(
        OutboxEventModel(
            event_type=PRICE_VERSION_PUBLISHED,
            event_version=1,
            payload={
                "partner_id": str(context.document.partner_id),
                "service_id": str(service_id),
                "price_version_id": str(published.id),
                "document_id": str(context.document.id),
            },
        )
    )
    context.document.status = "PUBLISHED"
    return published.id


def _audit_review_decision(
    session: Session,
    *,
    actor_id: UUID,
    action: str,
    task: ReviewTaskModel,
    before: dict[str, object],
    after: dict[str, object],
) -> AuditEventModel:
    audit_event = AuditEventModel(
        actor_id=actor_id,
        actor_type="operator",
        action=action,
        entity_type="review_task",
        entity_id=task.id,
        before_json=before,
        after_json=after,
        request_id=None,
        ip_address=None,
    )
    session.add(audit_event)
    session.flush()
    return audit_event


def _review_task_state(task: ReviewTaskModel) -> dict[str, object]:
    return {
        "task_id": str(task.id),
        "extracted_item_id": str(task.extracted_item_id),
        "status": task.status,
        "assigned_to": str(task.assigned_to) if task.assigned_to is not None else None,
        "version": task.version,
    }


def _decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
