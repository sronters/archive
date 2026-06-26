from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from medarchive_domain.ports import GraphRepository

from medarchive_application.graph_projection import GraphProjector


class GraphRebuildRepository(Protocol):
    def list_published_price_version_ids(self) -> tuple[UUID, ...]:
        ...


@dataclass(frozen=True)
class GraphRebuildResult:
    projected_price_versions: int


class GraphRebuilder:
    def __init__(
        self,
        *,
        graph_repository: GraphRepository,
        projection_repository: GraphRebuildRepository,
        projector: GraphProjector,
    ) -> None:
        self._graph_repository = graph_repository
        self._projection_repository = projection_repository
        self._projector = projector

    async def rebuild(self) -> GraphRebuildResult:
        await self._graph_repository.clear()
        price_version_ids = self._projection_repository.list_published_price_version_ids()
        for price_version_id in price_version_ids:
            await self._projector.project_price_version_published(price_version_id)
        return GraphRebuildResult(projected_price_versions=len(price_version_ids))
