from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from medarchive_application.outbox import PendingOutboxEvent
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import OutboxEventModel


class SqlAlchemyOutboxRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        statement: Select[tuple[OutboxEventModel]] = (
            select(OutboxEventModel)
            .where(OutboxEventModel.published_at.is_(None))
            .order_by(OutboxEventModel.created_at.asc())
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).scalars().all()
            return tuple(
                PendingOutboxEvent(
                    event_id=row.id,
                    event_type=row.event_type,
                    payload=row.payload,
                )
                for row in rows
            )

    def mark_published(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEventModel, event_id)
            if event is None:
                raise LookupError(f"Outbox event not found: {event_id}")
            event.published_at = datetime.now(timezone.utc)  # noqa: UP017
            session.commit()

    def increment_attempts(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEventModel, event_id)
            if event is None:
                raise LookupError(f"Outbox event not found: {event_id}")
            event.attempts += 1
            session.commit()
