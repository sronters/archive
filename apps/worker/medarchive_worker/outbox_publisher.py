from __future__ import annotations

import asyncio

from medarchive_application.outbox import OutboxPublisher
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
    )
    published = asyncio.run(publisher.publish_pending(limit=limit))
    return len(published)
