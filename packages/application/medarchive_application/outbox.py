from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from medarchive_domain.ports import TaskDispatcher

from medarchive_application.ingestion_orchestrator import DOCUMENT_PROCESSING_REQUESTED


@dataclass(frozen=True)
class PendingOutboxEvent:
    event_id: UUID
    event_type: str
    payload: dict[str, object]


@dataclass(frozen=True)
class PublishedOutboxEvent:
    event_id: UUID
    event_type: str


class OutboxRepository(Protocol):
    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        ...

    def mark_published(self, event_id: UUID) -> None:
        ...

    def increment_attempts(self, event_id: UUID) -> None:
        ...


class OutboxPublisher:
    def __init__(
        self,
        *,
        repository: OutboxRepository,
        task_dispatcher: TaskDispatcher,
    ) -> None:
        self._repository = repository
        self._task_dispatcher = task_dispatcher

    async def publish_pending(self, *, limit: int = 100) -> tuple[PublishedOutboxEvent, ...]:
        published: list[PublishedOutboxEvent] = []
        for event in self._repository.list_unpublished(limit=limit):
            try:
                await self._publish_event(event)
                self._repository.mark_published(event.event_id)
                published.append(
                    PublishedOutboxEvent(event_id=event.event_id, event_type=event.event_type)
                )
            except Exception:
                self._repository.increment_attempts(event.event_id)
                raise
        return tuple(published)

    async def _publish_event(self, event: PendingOutboxEvent) -> None:
        if event.event_type == DOCUMENT_PROCESSING_REQUESTED:
            document_id = _require_uuid(event.payload, "document_id")
            await self._task_dispatcher.dispatch_document_processing(document_id)
            return
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")


def _require_uuid(payload: dict[str, object], key: str) -> UUID:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Outbox payload missing string field: {key}")
    return UUID(value)
