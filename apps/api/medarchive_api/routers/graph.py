from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from medarchive_domain.ports import GraphNeighborhood, GraphRepository
from medarchive_infrastructure.graph import (
    ApacheAgeGraphRepository,
    NoOpGraphRepository,
    PostgresEdgeTableGraphRepository,
)
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles

MAX_RESPONSE_NODES = 200
MAX_RESPONSE_EDGES = 500


class GraphNodeResponse(BaseModel):
    id: str
    type: str
    entity_id: UUID | None
    external_id: str | None
    label: str
    properties: dict[str, object]


class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    type: str
    properties: dict[str, object]


class GraphNeighborhoodResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    truncated: bool = False


router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/services/{service_id}/neighborhood", response_model=GraphNeighborhoodResponse)
async def get_service_neighborhood(
    service_id: UUID,
    repository: Annotated[GraphRepository, Depends(get_graph_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("viewer", "operator", "administrator", "auditor")),
    ],
    depth: Annotated[int, Query(ge=1, le=2)] = 2,
) -> GraphNeighborhoodResponse:
    neighborhood = await repository.get_service_neighborhood(service_id, depth)
    return _response(neighborhood)


def get_graph_repository(settings: Annotated[Settings, Depends(get_settings)]) -> GraphRepository:
    session_factory = _session_factory(settings.database_url)
    if settings.graph_backend == "noop":
        return NoOpGraphRepository()
    if settings.graph_backend == "apache_age":
        return ApacheAgeGraphRepository(session_factory, graph_name=settings.graph_name)
    return PostgresEdgeTableGraphRepository(session_factory)


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _response(neighborhood: GraphNeighborhood) -> GraphNeighborhoodResponse:
    nodes = neighborhood.nodes[:MAX_RESPONSE_NODES]
    edges = neighborhood.edges[:MAX_RESPONSE_EDGES]
    returned_node_ids = {node.node_id for node in nodes}
    edges = tuple(
        edge
        for edge in edges
        if edge.source_node_id in returned_node_ids and edge.target_node_id in returned_node_ids
    )
    truncated = len(nodes) < len(neighborhood.nodes) or len(edges) < len(neighborhood.edges)
    return GraphNeighborhoodResponse(
        nodes=[
            GraphNodeResponse(
                id=node.node_id,
                type=node.node_type,
                entity_id=node.entity_id,
                external_id=node.external_id,
                label=node.label,
                properties=node.properties,
            )
            for node in nodes
        ],
        edges=[
            GraphEdgeResponse(
                source=edge.source_node_id,
                target=edge.target_node_id,
                type=edge.edge_type,
                properties=edge.properties,
            )
            for edge in edges
        ],
        truncated=truncated,
    )
