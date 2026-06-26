from __future__ import annotations

from uuid import uuid4

import pytest
from medarchive_application.ingestion_orchestrator import DOCUMENT_PROCESSING_REQUESTED
from medarchive_application.outbox import OutboxPublisher, PendingOutboxEvent

from tests.fakes import FakeOutboxRepository, FakeTaskDispatcher


@pytest.mark.asyncio
async def test_outbox_publisher_dispatches_processing_requested_event() -> None:
    document_id = uuid4()
    event_id = uuid4()
    repository = FakeOutboxRepository(
        (
            PendingOutboxEvent(
                event_id=event_id,
                event_type=DOCUMENT_PROCESSING_REQUESTED,
                event_version=1,
                payload={"document_id": str(document_id)},
            ),
        )
    )
    dispatcher = FakeTaskDispatcher()
    publisher = OutboxPublisher(repository=repository, task_dispatcher=dispatcher)

    published = await publisher.publish_pending()

    assert dispatcher.dispatched_document_ids == [document_id]
    assert repository.processing == [event_id]
    assert repository.published == [event_id]
    assert repository.attempted == []
    assert published[0].event_id == event_id


@pytest.mark.asyncio
async def test_outbox_publisher_retries_unknown_event_version() -> None:
    document_id = uuid4()
    event_id = uuid4()
    repository = FakeOutboxRepository(
        (
            PendingOutboxEvent(
                event_id=event_id,
                event_type=DOCUMENT_PROCESSING_REQUESTED,
                event_version=99,
                payload={"document_id": str(document_id)},
            ),
        )
    )

    with pytest.raises(ValueError, match="Unsupported outbox event version"):
        await OutboxPublisher(
            repository=repository,
            task_dispatcher=FakeTaskDispatcher(),
        ).publish_pending()

    assert repository.processing == [event_id]
    assert repository.published == []
    assert repository.attempted == [event_id]
