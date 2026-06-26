from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://medarchive:medarchive@localhost:5432/medarchive"
    redis_url: str = "redis://localhost:6379/1"
    celery_broker_url: str = "amqp://medarchive:medarchive@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/0"
    auth_mode: str = "local_jwt"
    local_api_keys: str = (
        "dev-admin:administrator,catalog_manager,senior_operator,operator,auditor,viewer,integration_client;"
        "dev-operator:operator,viewer;"
        "dev-integration:integration_client"
    )
    bearer_tokens: str = (
        "dev-oidc-admin:administrator,catalog_manager,senior_operator,operator,auditor,viewer;"
        "dev-oauth-integration:integration_client"
    )
    trusted_proxy_subject_header: str = "X-Forwarded-User"
    trusted_proxy_roles_header: str = "X-Forwarded-Roles"
    graph_backend: str = "postgres_edges"
    graph_name: str = "medarchive"
    malware_scanner_mode: str = "not_configured"
    local_storage_root: str = ".local_storage"
    max_upload_file_bytes: int = 50 * 1024 * 1024
    max_archive_file_count: int = 500
    max_archive_uncompressed_bytes: int = 500 * 1024 * 1024
    max_archive_compression_ratio: int = 100
    persistence_mode: str = "database"


def get_settings() -> Settings:
    return Settings()
