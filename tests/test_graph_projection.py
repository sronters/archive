from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from medarchive_application.graph_projection import GraphProjector, PriceVersionGraphProjection
from medarchive_application.graph_rebuild import GraphRebuilder
from medarchive_application.outbox import OutboxPublisher, PendingOutboxEvent

from tests.fakes import (
    FakeGraphProjectionRepository,
    FakeGraphRepository,
    FakeOutboxRepository,
    FakeTaskDispatcher,
)


@pytest.mark.asyncio
async def test_graph_projector_projects_published_price_version() -> None:
    projection = _projection()
    graph = FakeGraphRepository()

    await GraphProjector(
        graph_repository=graph,
        projection_repository=FakeGraphProjectionRepository(projection),
    ).project_price_version_published(projection.price_version_id)

    call_names = [name for name, _args in graph.calls]
    assert "upsert_partner" in call_names
    assert "upsert_service" in call_names
    assert "upsert_price_document" in call_names
    assert "upsert_price_version" in call_names
    assert "connect_partner_service" in call_names
    assert "connect_raw_name_to_service" in call_names


@pytest.mark.asyncio
async def test_outbox_publisher_projects_graph_event_before_marking_published() -> None:
    projection = _projection()
    event_id = uuid4()
    repository = FakeOutboxRepository(
        (
            PendingOutboxEvent(
                event_id=event_id,
                event_type="price_version.published",
                event_version=1,
                payload={"price_version_id": str(projection.price_version_id)},
            ),
        )
    )
    graph = FakeGraphRepository()

    published = await OutboxPublisher(
        repository=repository,
        task_dispatcher=FakeTaskDispatcher(),
        graph_projector=GraphProjector(
            graph_repository=graph,
            projection_repository=FakeGraphProjectionRepository(projection),
        ),
    ).publish_pending()

    assert published[0].event_id == event_id
    assert repository.processing == [event_id]
    assert repository.published == [event_id]
    assert graph.calls


@pytest.mark.asyncio
async def test_outbox_publisher_retries_graph_projection_failure() -> None:
    projection = _projection()
    event_id = uuid4()
    repository = FakeOutboxRepository(
        (
            PendingOutboxEvent(
                event_id=event_id,
                event_type="price_version.published",
                event_version=1,
                payload={"price_version_id": str(projection.price_version_id)},
            ),
        )
    )

    with pytest.raises(LookupError):
        await OutboxPublisher(
            repository=repository,
            task_dispatcher=FakeTaskDispatcher(),
            graph_projector=GraphProjector(
                graph_repository=FakeGraphRepository(),
                projection_repository=FakeGraphProjectionRepository(_projection()),
            ),
        ).publish_pending()

    assert repository.published == []
    assert repository.attempted == [event_id]


@pytest.mark.asyncio
async def test_graph_projector_links_superseded_price_version() -> None:
    projection = _projection()
    old_price_version_id = uuid4()
    projection = replace(projection, superseded_price_version_id=old_price_version_id)
    graph = FakeGraphRepository()

    await GraphProjector(
        graph_repository=graph,
        projection_repository=FakeGraphProjectionRepository(projection),
    ).project_price_version_published(projection.price_version_id)

    assert (
        "connect_price_version_superseded",
        (old_price_version_id, projection.price_version_id),
    ) in graph.calls


@pytest.mark.asyncio
async def test_graph_rebuild_clears_and_replays_published_price_versions() -> None:
    projection = _projection()
    graph = FakeGraphRepository()
    projection_repository = FakeGraphProjectionRepository(projection)
    projector = GraphProjector(
        graph_repository=graph,
        projection_repository=projection_repository,
    )

    result = await GraphRebuilder(
        graph_repository=graph,
        projection_repository=projection_repository,
        projector=projector,
    ).rebuild()

    assert result.projected_price_versions == 1
    assert graph.calls[0] == ("clear", ())
    assert any(call_name == "upsert_price_version" for call_name, _args in graph.calls)


def _projection() -> PriceVersionGraphProjection:
    return PriceVersionGraphProjection(
        price_version_id=uuid4(),
        partner_id=uuid4(),
        external_partner_id="clinic-001",
        partner_name="Medical Center",
        service_id=uuid4(),
        external_service_id="svc-001",
        service_name="MRI brain",
        service_category="diagnostics",
        document_id=uuid4(),
        external_source_id="upload-001",
        raw_service_name="MR tomographiya golovy",
        match_confidence=0.984,
        confirmed=True,
        status="published",
    )
