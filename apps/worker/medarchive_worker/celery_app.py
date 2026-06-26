from __future__ import annotations

from celery import Celery

from medarchive_worker.config import get_worker_settings

settings = get_worker_settings()

celery_app = Celery(
    "medarchive",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["medarchive_worker.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="medarchive.default",
)
