from __future__ import annotations

from uuid import UUID

from medarchive_application.graph_projection import PriceVersionGraphProjection
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import (
    ExtractedPriceItemModel,
    PartnerModel,
    PriceDocumentModel,
    PriceVersionModel,
    ProcessingRunModel,
    ServiceMatchModel,
    ServiceModel,
)


class SqlAlchemyGraphProjectionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_price_version_projection(
        self,
        price_version_id: UUID,
    ) -> PriceVersionGraphProjection:
        with self._session_factory() as session:
            statement = (
                select(
                    PriceVersionModel,
                    PartnerModel,
                    ServiceModel,
                    PriceDocumentModel,
                    ExtractedPriceItemModel,
                    ServiceMatchModel,
                )
                .join(PartnerModel, PartnerModel.id == PriceVersionModel.partner_id)
                .join(ServiceModel, ServiceModel.id == PriceVersionModel.service_id)
                .join(
                    PriceDocumentModel,
                    PriceDocumentModel.id == PriceVersionModel.source_document_id,
                )
                .join(ProcessingRunModel, ProcessingRunModel.document_id == PriceDocumentModel.id)
                .join(
                    ExtractedPriceItemModel,
                    ExtractedPriceItemModel.processing_run_id == ProcessingRunModel.id,
                    isouter=True,
                )
                .join(
                    ServiceMatchModel,
                    (ServiceMatchModel.extracted_item_id == ExtractedPriceItemModel.id)
                    & (ServiceMatchModel.service_id == ServiceModel.id),
                    isouter=True,
                )
                .where(PriceVersionModel.id == price_version_id)
                .order_by(ServiceMatchModel.rank.asc().nulls_last())
                .limit(1)
            )
            row = session.execute(statement).one_or_none()
            if row is None:
                raise LookupError(f"Price version not found: {price_version_id}")
            price_version, partner, service, document, extracted_item, service_match = row
            superseded_price_version_id = session.execute(
                select(PriceVersionModel.id).where(
                    PriceVersionModel.superseded_by == price_version.id
                )
            ).scalar_one_or_none()
            return PriceVersionGraphProjection(
                price_version_id=price_version.id,
                partner_id=partner.id,
                external_partner_id=partner.external_partner_id,
                partner_name=partner.name,
                service_id=service.id,
                external_service_id=service.external_service_id,
                service_name=service.official_name,
                service_category=service.category,
                document_id=document.id,
                external_source_id=document.external_source_id,
                raw_service_name=(
                    extracted_item.service_name_raw if extracted_item is not None else None
                ),
                match_confidence=(
                    float(service_match.reranker_score or service_match.retrieval_score)
                    if service_match is not None
                    else None
                ),
                confirmed=price_version.verification_status == "published",
                status=price_version.verification_status,
                superseded_price_version_id=superseded_price_version_id,
            )

    def list_published_price_version_ids(self) -> tuple[UUID, ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(PriceVersionModel.id)
                .where(PriceVersionModel.verification_status == "published")
                .order_by(PriceVersionModel.published_at.asc(), PriceVersionModel.id.asc())
            ).scalars()
            return tuple(rows)
