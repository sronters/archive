from __future__ import annotations

import json

from medarchive_application.catalog_import import CatalogImportService

from tests.fakes import FakeCatalogImportRepository


def test_service_catalog_preview_reports_duplicate_external_ids() -> None:
    service = CatalogImportService(repository=FakeCatalogImportRepository())
    content = json.dumps(
        [
            {"external_service_id": "svc-001", "official_name": "MRI brain"},
            {"external_service_id": "svc-001", "official_name": "MRI duplicate"},
        ]
    ).encode()

    report = service.preview_services(content)

    assert report.mode == "preview"
    assert report.total_rows == 2
    assert report.valid_rows == 1
    assert report.issues[0].code == "duplicate_external_service_id"


def test_partner_catalog_apply_is_blocked_when_payload_has_issues() -> None:
    repository = FakeCatalogImportRepository()
    service = CatalogImportService(repository=repository)
    content = json.dumps([{"external_partner_id": "clinic-001"}]).encode()

    report = service.apply_partners(content, actor_id=None)

    assert report.issues[0].code == "missing_partner_name"
    assert repository.applied_partners == ()
