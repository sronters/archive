from __future__ import annotations

from datetime import datetime, timezone

from medarchive_application.catalog_import import PartnerCatalogRecord, ServiceCatalogRecord
from medarchive_application.remote_catalog_sync import (
    RemoteCatalogSyncService,
    RemotePartnerCatalogSnapshot,
    RemoteServiceCatalogSnapshot,
    ScheduledCatalogSyncRunner,
)

from tests.fakes import FakeCatalogImportRepository


def test_remote_catalog_sync_applies_services_with_cursor() -> None:
    repository = FakeCatalogImportRepository()
    service = RemoteCatalogSyncService(client=_FakeRemoteCatalogClient(), repository=repository)

    result = service.sync_services(cursor="old", actor_id=None)

    assert result.entity_type == "service"
    assert result.cursor == "svc-next"
    assert result.report.mode == "remote_sync"
    assert result.report.created_count == 1
    assert repository.applied_services[0].external_service_id == "svc-remote"


def test_scheduled_catalog_sync_runs_service_and_partner_sync() -> None:
    repository = FakeCatalogImportRepository()
    service = RemoteCatalogSyncService(client=_FakeRemoteCatalogClient(), repository=repository)

    service_result, partner_result = ScheduledCatalogSyncRunner(sync_service=service).run(
        service_cursor=None,
        partner_cursor=None,
    )

    assert service_result.cursor == "svc-next"
    assert partner_result.cursor == "partner-next"
    assert repository.applied_services[0].external_service_id == "svc-remote"
    assert repository.applied_partners[0].external_partner_id == "clinic-remote"


class _FakeRemoteCatalogClient:
    def fetch_services(self, *, cursor: str | None) -> RemoteServiceCatalogSnapshot:
        assert cursor in {"old", None}
        return RemoteServiceCatalogSnapshot(
            records=(
                ServiceCatalogRecord(
                    external_service_id="svc-remote",
                    official_name="MRI brain",
                    synonyms=("MR brain",),
                    category="diagnostics",
                    is_active=True,
                ),
            ),
            cursor="svc-next",
            fetched_at=datetime.now(timezone.utc),  # noqa: UP017
        )

    def fetch_partners(self, *, cursor: str | None) -> RemotePartnerCatalogSnapshot:
        assert cursor is None
        return RemotePartnerCatalogSnapshot(
            records=(
                PartnerCatalogRecord(
                    external_partner_id="clinic-remote",
                    name="Remote Clinic",
                    bin="123456789012",
                    city="Astana",
                    is_active=True,
                ),
            ),
            cursor="partner-next",
            fetched_at=datetime.now(timezone.utc),  # noqa: UP017
        )
