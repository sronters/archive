from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ServiceCatalogRecord:
    external_service_id: str
    official_name: str
    synonyms: tuple[str, ...]
    category: str | None
    is_active: bool


@dataclass(frozen=True)
class PartnerCatalogRecord:
    external_partner_id: str
    name: str
    bin: str | None
    city: str | None
    is_active: bool


@dataclass(frozen=True)
class CatalogImportIssue:
    row_number: int
    external_id: str | None
    code: str
    detail: str


@dataclass(frozen=True)
class CatalogImportReport:
    mode: str
    entity_type: str
    total_rows: int
    valid_rows: int
    created_count: int
    updated_count: int
    deactivated_count: int
    issues: tuple[CatalogImportIssue, ...]


class CatalogImportRepository(Protocol):
    def preview_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        ...

    def apply_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        ...

    def preview_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        ...

    def apply_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        ...


class CatalogImportService:
    def __init__(self, *, repository: CatalogImportRepository) -> None:
        self._repository = repository

    def preview_services(self, content: bytes) -> CatalogImportReport:
        records, issues, total_rows = parse_service_catalog_json(content)
        created, updated, deactivated = self._repository.preview_services(records)
        return _report(
            mode="preview",
            entity_type="service",
            total_rows=total_rows,
            records=records,
            issues=issues,
            created=created,
            updated=updated,
            deactivated=deactivated,
        )

    def apply_services(
        self,
        content: bytes,
        *,
        actor_id: UUID | None,
    ) -> CatalogImportReport:
        records, issues, total_rows = parse_service_catalog_json(content)
        if issues:
            return _report(
                mode="apply",
                entity_type="service",
                total_rows=total_rows,
                records=records,
                issues=issues,
                created=0,
                updated=0,
                deactivated=0,
            )
        created, updated, deactivated = self._repository.apply_services(records, actor_id=actor_id)
        return _report(
            mode="apply",
            entity_type="service",
            total_rows=total_rows,
            records=records,
            issues=issues,
            created=created,
            updated=updated,
            deactivated=deactivated,
        )

    def preview_partners(self, content: bytes) -> CatalogImportReport:
        records, issues, total_rows = parse_partner_catalog_json(content)
        created, updated, deactivated = self._repository.preview_partners(records)
        return _report(
            mode="preview",
            entity_type="partner",
            total_rows=total_rows,
            records=records,
            issues=issues,
            created=created,
            updated=updated,
            deactivated=deactivated,
        )

    def apply_partners(
        self,
        content: bytes,
        *,
        actor_id: UUID | None,
    ) -> CatalogImportReport:
        records, issues, total_rows = parse_partner_catalog_json(content)
        if issues:
            return _report(
                mode="apply",
                entity_type="partner",
                total_rows=total_rows,
                records=records,
                issues=issues,
                created=0,
                updated=0,
                deactivated=0,
            )
        created, updated, deactivated = self._repository.apply_partners(records, actor_id=actor_id)
        return _report(
            mode="apply",
            entity_type="partner",
            total_rows=total_rows,
            records=records,
            issues=issues,
            created=created,
            updated=updated,
            deactivated=deactivated,
        )


def parse_service_catalog_json(
    content: bytes,
) -> tuple[tuple[ServiceCatalogRecord, ...], tuple[CatalogImportIssue, ...], int]:
    rows = _load_json_rows(content)
    records: list[ServiceCatalogRecord] = []
    issues: list[CatalogImportIssue] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        external_id = _clean_string(row.get("external_service_id"))
        official_name = _clean_string(row.get("official_name"))
        if external_id is None:
            issues.append(_issue(index, None, "missing_external_service_id"))
            continue
        if external_id in seen:
            issues.append(_issue(index, external_id, "duplicate_external_service_id"))
            continue
        seen.add(external_id)
        if official_name is None:
            issues.append(_issue(index, external_id, "missing_official_name"))
            continue
        synonyms = row.get("synonyms", [])
        if not isinstance(synonyms, list):
            issues.append(_issue(index, external_id, "invalid_synonyms"))
            continue
        records.append(
            ServiceCatalogRecord(
                external_service_id=external_id,
                official_name=official_name,
                synonyms=tuple(
                    synonym
                    for item in synonyms
                    if (synonym := str(item).strip())
                ),
                category=_clean_string(row.get("category")),
                is_active=bool(row.get("is_active", True)),
            )
        )
    return tuple(records), tuple(issues), len(rows)


def parse_partner_catalog_json(
    content: bytes,
) -> tuple[tuple[PartnerCatalogRecord, ...], tuple[CatalogImportIssue, ...], int]:
    rows = _load_json_rows(content)
    records: list[PartnerCatalogRecord] = []
    issues: list[CatalogImportIssue] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        external_id = _clean_string(row.get("external_partner_id"))
        name = _clean_string(row.get("name"))
        if external_id is None:
            issues.append(_issue(index, None, "missing_external_partner_id"))
            continue
        if external_id in seen:
            issues.append(_issue(index, external_id, "duplicate_external_partner_id"))
            continue
        seen.add(external_id)
        if name is None:
            issues.append(_issue(index, external_id, "missing_partner_name"))
            continue
        records.append(
            PartnerCatalogRecord(
                external_partner_id=external_id,
                name=name,
                bin=_clean_string(row.get("bin")),
                city=_clean_string(row.get("city")),
                is_active=bool(row.get("is_active", True)),
            )
        )
    return tuple(records), tuple(issues), len(rows)


def _load_json_rows(content: bytes) -> list[dict[str, object]]:
    payload = json.loads(content.decode("utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        raise ValueError("Catalog import JSON must be a list or an object with an items list.")
    rows: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Catalog import rows must be JSON objects.")
        rows.append(item)
    return rows


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _issue(row_number: int, external_id: str | None, code: str) -> CatalogImportIssue:
    return CatalogImportIssue(
        row_number=row_number,
        external_id=external_id,
        code=code,
        detail=code.replace("_", " "),
    )


def _report(
    *,
    mode: str,
    entity_type: str,
    total_rows: int,
    records: tuple[object, ...],
    issues: tuple[CatalogImportIssue, ...],
    created: int,
    updated: int,
    deactivated: int,
) -> CatalogImportReport:
    return CatalogImportReport(
        mode=mode,
        entity_type=entity_type,
        total_rows=total_rows,
        valid_rows=len(records),
        created_count=created,
        updated_count=updated,
        deactivated_count=deactivated,
        issues=issues,
    )
