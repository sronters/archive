from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://medarchive:medarchive@localhost:5432/medarchive"
    celery_broker_url: str = "amqp://medarchive:medarchive@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/0"
    local_storage_root: str = ".local_storage"
    remote_service_catalog_url: str = "http://localhost:8000/mock/service-catalog"
    remote_partner_catalog_url: str = "http://localhost:8000/mock/partners"
    remote_catalog_bearer_token: str | None = None


def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
