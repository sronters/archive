from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from medarchive_domain.ports import GraphRepository

PRICE_VERSION_PUBLISHED = "price_version.published"


@dataclass(frozen=True)
class PriceVersionGraphProjection:
    price_version_id: UUID
    partner_id: UUID
    external_partner_id: str | None
    partner_name: str
    service_id: UUID
    external_service_id: str | None
    service_name: str
    service_category: str | None
    document_id: UUID
    external_source_id: str | None
    raw_service_name: str | None
    match_confidence: float | None
    confirmed: bool
    status: str
    superseded_price_version_id: UUID | None = None


class GraphProjectionRepository(Protocol):
    def get_price_version_projection(
        self,
        price_version_id: UUID,
    ) -> PriceVersionGraphProjection:
        ...


class GraphProjector:
    def __init__(
        self,
        *,
        graph_repository: GraphRepository,
        projection_repository: GraphProjectionRepository,
    ) -> None:
        self._graph_repository = graph_repository
        self._projection_repository = projection_repository

    async def project_price_version_published(self, price_version_id: UUID) -> None:
        projection = self._projection_repository.get_price_version_projection(price_version_id)
        await self._graph_repository.upsert_partner(
            projection.partner_id,
            projection.external_partner_id,
            projection.partner_name,
        )
        await self._graph_repository.upsert_service(
            projection.service_id,
            projection.external_service_id,
            projection.service_name,
            projection.service_category,
        )
        await self._graph_repository.upsert_price_document(
            projection.document_id,
            projection.external_source_id,
            label=f"Document {projection.external_source_id or projection.document_id}",
        )
        await self._graph_repository.upsert_price_version(
            projection.price_version_id,
            projection.service_id,
            projection.document_id,
            projection.status,
        )
        if projection.superseded_price_version_id:
            await self._graph_repository.connect_price_version_superseded(
                projection.superseded_price_version_id,
                projection.price_version_id,
            )
        await self._graph_repository.connect_partner_service(
            projection.partner_id,
            projection.service_id,
        )
        if projection.raw_service_name:
            await self._graph_repository.connect_raw_name_to_service(
                raw_name=projection.raw_service_name,
                partner_id=projection.partner_id,
                service_id=projection.service_id,
                confidence=projection.match_confidence or 0.0,
                confirmed=projection.confirmed,
            )
