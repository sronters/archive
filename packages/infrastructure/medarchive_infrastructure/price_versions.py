from __future__ import annotations

from datetime import datetime
from uuid import UUID

from medarchive_application.price_versions import PriceVersionRead
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    PartnerModel,
    PriceDocumentModel,
    PriceVersionModel,
    ServiceModel,
)


class SqlAlchemyPriceVersionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_price_versions(
        self,
        *,
        verification_status: str | None,
        partner_id: UUID | None,
        service_id: UUID | None,
        external_partner_id: str | None,
        external_service_id: str | None,
        changed_since: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[PriceVersionRead, ...]:
        with self._session_factory() as session:
            statement = (
                select(
                    PriceVersionModel,
                    PartnerModel.external_partner_id,
                    PartnerModel.name.label("partner_name"),
                    ServiceModel.external_service_id,
                    ServiceModel.official_name.label("service_name"),
                    PriceDocumentModel.external_source_id,
                )
                .join(PartnerModel, PartnerModel.id == PriceVersionModel.partner_id)
                .join(ServiceModel, ServiceModel.id == PriceVersionModel.service_id)
                .join(
                    PriceDocumentModel,
                    PriceDocumentModel.id == PriceVersionModel.source_document_id,
                )
                .order_by(PriceVersionModel.updated_at.desc(), PriceVersionModel.id.asc())
            )
            if verification_status is not None:
                statement = statement.where(
                    PriceVersionModel.verification_status == verification_status,
                )
            if partner_id is not None:
                statement = statement.where(PriceVersionModel.partner_id == partner_id)
            if service_id is not None:
                statement = statement.where(PriceVersionModel.service_id == service_id)
            if external_partner_id is not None:
                statement = statement.where(PartnerModel.external_partner_id == external_partner_id)
            if external_service_id is not None:
                statement = statement.where(ServiceModel.external_service_id == external_service_id)
            if changed_since is not None:
                statement = statement.where(PriceVersionModel.updated_at > changed_since)

            rows = session.execute(statement.limit(limit).offset(offset)).all()
            return tuple(
                PriceVersionRead(
                    price_version_id=row.PriceVersionModel.id,
                    partner_id=row.PriceVersionModel.partner_id,
                    external_partner_id=row.external_partner_id,
                    partner_name=row.partner_name,
                    service_id=row.PriceVersionModel.service_id,
                    external_service_id=row.external_service_id,
                    service_name=row.service_name,
                    source_document_id=row.PriceVersionModel.source_document_id,
                    external_source_id=row.external_source_id,
                    resident_price_kzt=row.PriceVersionModel.resident_price_kzt,
                    nonresident_price_kzt=row.PriceVersionModel.nonresident_price_kzt,
                    original_price=row.PriceVersionModel.original_price,
                    original_currency=row.PriceVersionModel.original_currency,
                    exchange_rate=row.PriceVersionModel.exchange_rate,
                    valid_from=row.PriceVersionModel.valid_from,
                    valid_to=row.PriceVersionModel.valid_to,
                    published_at=row.PriceVersionModel.published_at,
                    verification_status=row.PriceVersionModel.verification_status,
                    updated_at=row.PriceVersionModel.updated_at,
                )
                for row in rows
            )
