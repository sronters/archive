from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from medarchive_application.catalog_import import PartnerCatalogRecord, ServiceCatalogRecord
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import AuditEventModel, PartnerModel, ServiceModel


class _CatalogRecord(Protocol):
    @property
    def is_active(self) -> bool:
        ...


class SqlAlchemyCatalogImportRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def preview_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        with self._session_factory() as session:
            existing = _services_by_external_id(session, records)
            return _preview_counts(
                records=records,
                existing=existing,
                external_id_attr="external_service_id",
            )

    def apply_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        with self._session_factory() as session:
            existing = _services_by_external_id(session, records)
            created = 0
            updated = 0
            deactivated = 0
            for record in records:
                row = existing.get(record.external_service_id)
                if row is None:
                    row = ServiceModel(
                        external_service_id=record.external_service_id,
                        official_name=record.official_name,
                        synonyms=list(record.synonyms),
                        category=record.category,
                        is_active=record.is_active,
                    )
                    session.add(row)
                    session.flush()
                    created += 1
                else:
                    row.official_name = record.official_name
                    row.synonyms = list(record.synonyms)
                    row.category = record.category
                    row.is_active = record.is_active
                    updated += 1
                if not record.is_active:
                    deactivated += 1
                _audit_import(
                    session,
                    actor_id=actor_id,
                    action="service_catalog.imported",
                    entity_type="service",
                    entity_id=row.id,
                    after_json={
                        "external_service_id": record.external_service_id,
                        "official_name": record.official_name,
                        "is_active": record.is_active,
                    },
                )
            session.commit()
            return created, updated, deactivated

    def preview_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        with self._session_factory() as session:
            existing = _partners_by_external_id(session, records)
            return _preview_counts(
                records=records,
                existing=existing,
                external_id_attr="external_partner_id",
            )

    def apply_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        with self._session_factory() as session:
            existing = _partners_by_external_id(session, records)
            created = 0
            updated = 0
            deactivated = 0
            for record in records:
                row = existing.get(record.external_partner_id)
                if row is None:
                    row = PartnerModel(
                        external_partner_id=record.external_partner_id,
                        name=record.name,
                        bin=record.bin,
                        city=record.city,
                        is_active=record.is_active,
                    )
                    session.add(row)
                    session.flush()
                    created += 1
                else:
                    row.name = record.name
                    row.bin = record.bin
                    row.city = record.city
                    row.is_active = record.is_active
                    updated += 1
                if not record.is_active:
                    deactivated += 1
                _audit_import(
                    session,
                    actor_id=actor_id,
                    action="partner_catalog.imported",
                    entity_type="partner",
                    entity_id=row.id,
                    after_json={
                        "external_partner_id": record.external_partner_id,
                        "name": record.name,
                        "is_active": record.is_active,
                    },
                )
            session.commit()
            return created, updated, deactivated


def _services_by_external_id(
    session: Session,
    records: tuple[ServiceCatalogRecord, ...],
) -> dict[str, ServiceModel]:
    external_ids = [record.external_service_id for record in records]
    if not external_ids:
        return {}
    rows = session.execute(
        select(ServiceModel).where(ServiceModel.external_service_id.in_(external_ids)),
    ).scalars()
    return {row.external_service_id: row for row in rows if row.external_service_id is not None}


def _partners_by_external_id(
    session: Session,
    records: tuple[PartnerCatalogRecord, ...],
) -> dict[str, PartnerModel]:
    external_ids = [record.external_partner_id for record in records]
    if not external_ids:
        return {}
    rows = session.execute(
        select(PartnerModel).where(PartnerModel.external_partner_id.in_(external_ids)),
    ).scalars()
    return {row.external_partner_id: row for row in rows if row.external_partner_id is not None}


def _preview_counts(
    *,
    records: Sequence[_CatalogRecord],
    existing: Mapping[str, object],
    external_id_attr: str,
) -> tuple[int, int, int]:
    created = 0
    updated = 0
    deactivated = 0
    for record in records:
        external_id = getattr(record, external_id_attr)
        if external_id in existing:
            updated += 1
        else:
            created += 1
        if not record.is_active:
            deactivated += 1
    return created, updated, deactivated


def _audit_import(
    session: Session,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID,
    after_json: dict[str, object],
) -> None:
    session.add(
        AuditEventModel(
            actor_id=actor_id,
            actor_type="operator" if actor_id is not None else "system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=None,
            after_json=after_json,
            request_id=None,
            ip_address=None,
        )
    )
