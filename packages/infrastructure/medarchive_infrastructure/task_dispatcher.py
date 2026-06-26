from __future__ import annotations

from uuid import UUID

from celery import Celery


class CeleryTaskDispatcher:
    def __init__(self, celery_app: Celery) -> None:
        self._celery_app = celery_app

    async def dispatch_document_processing(self, document_id: UUID) -> None:
        self._celery_app.send_task("medarchive.process_document", args=[str(document_id)])
