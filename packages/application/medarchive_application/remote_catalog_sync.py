from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from medarchive_application.catalog_import import (
    CatalogImportReport,
    CatalogImportRepository,
    PartnerCatalogRecord,
    ServiceCatalogRecord,
    _report,
)


@dataclass(frozen=True)
class RemoteServiceCatalogSnapshot:
    records: tuple[ServiceCatalogRecord, ...]
    cursor: str | None
    fetched_at: datetime


@dataclass(frozen=True)
class RemotePartnerCatalogSnapshot:
    records: tuple[PartnerCatalogRecord, ...]
    cursor: str | None
    fetched_at: datetime


@dataclass(frozen=True)
class RemoteCatalogSyncResult:
    entity_type: str
    cursor: str | None
    fetched_at: datetime
    report: CatalogImportReport


class RemoteCatalogClient(Protocol):
    def fetch_services(self, *, cursor: str | None) -> RemoteServiceCatalogSnapshot:
        ...

    def fetch_partners(self, *, cursor: str | None) -> RemotePartnerCatalogSnapshot:
        ...


class RemoteCatalogSyncService:
    def __init__(
        self,
        *,
        client: RemoteCatalogClient,
        repository: CatalogImportRepository,
    ) -> None:
        self._client = client
        self._repository = repository

    def sync_services(
        self,
        *,
        cursor: str | None,
        actor_id: UUID | None,
    ) -> RemoteCatalogSyncResult:
        snapshot = self._client.fetch_services(cursor=cursor)
        created, updated, deactivated = self._repository.apply_services(
            snapshot.records,
            actor_id=actor_id,
        )
        return RemoteCatalogSyncResult(
            entity_type="service",
            cursor=snapshot.cursor,
            fetched_at=snapshot.fetched_at,
            report=_report(
                mode="remote_sync",
                entity_type="service",
                total_rows=len(snapshot.records),
                records=snapshot.records,
                issues=(),
                created=created,
                updated=updated,
                deactivated=deactivated,
            ),
        )

    def sync_partners(
        self,
        *,
        cursor: str | None,
        actor_id: UUID | None,
    ) -> RemoteCatalogSyncResult:
        snapshot = self._client.fetch_partners(cursor=cursor)
        created, updated, deactivated = self._repository.apply_partners(
            snapshot.records,
            actor_id=actor_id,
        )
        return RemoteCatalogSyncResult(
            entity_type="partner",
            cursor=snapshot.cursor,
            fetched_at=snapshot.fetched_at,
            report=_report(
                mode="remote_sync",
                entity_type="partner",
                total_rows=len(snapshot.records),
                records=snapshot.records,
                issues=(),
                created=created,
                updated=updated,
                deactivated=deactivated,
            ),
        )


class ScheduledCatalogSyncRunner:
    def __init__(self, *, sync_service: RemoteCatalogSyncService) -> None:
        self._sync_service = sync_service

    def run(
        self,
        *,
        service_cursor: str | None,
        partner_cursor: str | None,
        actor_id: UUID | None = None,
    ) -> tuple[RemoteCatalogSyncResult, RemoteCatalogSyncResult]:
        service_result = self._sync_service.sync_services(
            cursor=service_cursor,
            actor_id=actor_id,
        )
        partner_result = self._sync_service.sync_partners(
            cursor=partner_cursor,
            actor_id=actor_id,
        )
        return service_result, partner_result
