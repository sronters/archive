from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from medarchive_domain.ports import TaskDispatcher

from medarchive_application.graph_projection import PRICE_VERSION_PUBLISHED, GraphProjector
from medarchive_application.ingestion_orchestrator import DOCUMENT_PROCESSING_REQUESTED


@dataclass(frozen=True)
class PendingOutboxEvent:
    event_id: UUID
    event_type: str
    event_version: int
    payload: dict[str, object]


@dataclass(frozen=True)
class PublishedOutboxEvent:
    event_id: UUID
    event_type: str


class OutboxRepository(Protocol):
    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        ...

    def mark_processing(self, event_id: UUID) -> None:
        ...

    def mark_published(self, event_id: UUID) -> None:
        ...

    def mark_retry(
        self,
        event_id: UUID,
        *,
        error: str,
        next_retry_at: datetime | None,
        max_attempts: int,
    ) -> None:
        ...


class OutboxPublisher:
    def __init__(
        self,
        *,
        repository: OutboxRepository,
        task_dispatcher: TaskDispatcher,
        graph_projector: GraphProjector | None = None,
        max_attempts: int = 5,
    ) -> None:
        self._repository = repository
        self._task_dispatcher = task_dispatcher
        self._graph_projector = graph_projector
        self._max_attempts = max_attempts

    async def publish_pending(self, *, limit: int = 100) -> tuple[PublishedOutboxEvent, ...]:
        published: list[PublishedOutboxEvent] = []
        for event in self._repository.list_unpublished(limit=limit):
            try:
                self._repository.mark_processing(event.event_id)
                await self._publish_event(event)
                self._repository.mark_published(event.event_id)
                published.append(
                    PublishedOutboxEvent(event_id=event.event_id, event_type=event.event_type)
                )
            except Exception as exc:
                self._repository.mark_retry(
                    event.event_id,
                    error=str(exc),
                    next_retry_at=None,
                    max_attempts=self._max_attempts,
                )
                raise
        return tuple(published)

    async def _publish_event(self, event: PendingOutboxEvent) -> None:
        if event.event_version != 1:
            raise ValueError(
                f"Unsupported outbox event version: {event.event_type} v{event.event_version}"
            )
        if event.event_type == DOCUMENT_PROCESSING_REQUESTED:
            document_id = _require_uuid(event.payload, "document_id")
            await self._task_dispatcher.dispatch_document_processing(document_id)
            return
        if event.event_type == PRICE_VERSION_PUBLISHED:
            if self._graph_projector is None:
                raise ValueError("Graph projector is not configured.")
            price_version_id = _require_uuid(event.payload, "price_version_id")
            await self._graph_projector.project_price_version_published(price_version_id)
            return
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")


def _require_uuid(payload: dict[str, object], key: str) -> UUID:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Outbox payload missing string field: {key}")
    return UUID(value)
