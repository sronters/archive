from __future__ import annotations

import asyncio

from medarchive_application.graph_projection import GraphProjector
from medarchive_application.outbox import OutboxPublisher
from medarchive_infrastructure.graph import (
    ApacheAgeGraphRepository,
    NoOpGraphRepository,
    PostgresEdgeTableGraphRepository,
)
from medarchive_infrastructure.graph_projection import SqlAlchemyGraphProjectionRepository
from medarchive_infrastructure.outbox import SqlAlchemyOutboxRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from medarchive_infrastructure.task_dispatcher import CeleryTaskDispatcher

from medarchive_worker.celery_app import celery_app
from medarchive_worker.config import get_worker_settings


def publish_outbox_once(limit: int = 100) -> int:
    settings = get_worker_settings()
    session_factory = create_session_factory(create_sync_engine(settings.database_url))
    publisher = OutboxPublisher(
        repository=SqlAlchemyOutboxRepository(session_factory),
        task_dispatcher=CeleryTaskDispatcher(celery_app),
        graph_projector=GraphProjector(
            graph_repository=_graph_repository(
                settings.graph_backend,
                settings.graph_name,
                session_factory,
            ),
            projection_repository=SqlAlchemyGraphProjectionRepository(session_factory),
        ),
    )
    published = asyncio.run(publisher.publish_pending(limit=limit))
    return len(published)


def _graph_repository(
    backend: str,
    graph_name: str,
    session_factory: object,
) -> NoOpGraphRepository | PostgresEdgeTableGraphRepository | ApacheAgeGraphRepository:
    if backend == "noop":
        return NoOpGraphRepository()
    if backend == "apache_age":
        return ApacheAgeGraphRepository(session_factory, graph_name=graph_name)  # type: ignore[arg-type]
    return PostgresEdgeTableGraphRepository(session_factory)  # type: ignore[arg-type]
