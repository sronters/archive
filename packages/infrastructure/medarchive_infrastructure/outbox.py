from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from medarchive_application.outbox import PendingOutboxEvent
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import OutboxEventModel


class SqlAlchemyOutboxRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        now = datetime.now(timezone.utc)  # noqa: UP017
        statement: Select[tuple[OutboxEventModel]] = (
            select(OutboxEventModel)
            .where(OutboxEventModel.published_at.is_(None))
            .where(OutboxEventModel.status.in_(("pending", "retrying")))
            .where(
                or_(
                    OutboxEventModel.next_retry_at.is_(None),
                    OutboxEventModel.next_retry_at <= now,
                )
            )
            .order_by(OutboxEventModel.created_at.asc())
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).scalars().all()
            return tuple(
                PendingOutboxEvent(
                    event_id=row.id,
                    event_type=row.event_type,
                    event_version=row.event_version,
                    payload=row.payload,
                )
                for row in rows
            )

    def mark_processing(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEventModel, event_id)
            if event is None:
                raise LookupError(f"Outbox event not found: {event_id}")
            event.status = "processing"
            event.processing_started_at = datetime.now(timezone.utc)  # noqa: UP017
            session.commit()

    def mark_published(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEventModel, event_id)
            if event is None:
                raise LookupError(f"Outbox event not found: {event_id}")
            now = datetime.now(timezone.utc)  # noqa: UP017
            event.status = "completed"
            event.published_at = now
            event.processed_at = now
            event.last_error = None
            event.next_retry_at = None
            session.commit()

    def mark_retry(
        self,
        event_id: UUID,
        *,
        error: str,
        next_retry_at: datetime | None,
        max_attempts: int,
    ) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEventModel, event_id)
            if event is None:
                raise LookupError(f"Outbox event not found: {event_id}")
            event.attempts += 1
            event.last_error = error[:4000]
            if event.attempts >= max_attempts:
                event.status = "dead_letter"
                event.next_retry_at = None
            else:
                event.status = "retrying"
                event.next_retry_at = next_retry_at or _next_retry_at(event.attempts)
            session.commit()


def _next_retry_at(attempts: int) -> datetime:
    delay_seconds = min(3600, 60 * (2 ** max(attempts - 1, 0)))
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)  # noqa: UP017
