from __future__ import annotations

from uuid import UUID, uuid4

from medarchive_domain.ports import GraphEdge, GraphNeighborhood, GraphNode
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import GraphEdgeModel, GraphNodeModel

ALLOWED_GRAPH_EDGE_TYPES = frozenset(
    {
        "BELONGS_TO",
        "CONFIRMED_AS",
        "EXTRACTED_FROM",
        "HAS_PRICE",
        "MATCHED_TO",
        "OFFERS",
        "SUPERSEDED_BY",
    }
)
MAX_GRAPH_NODES = 200
MAX_GRAPH_EDGES = 500


class NoOpGraphRepository:
    async def clear(self) -> None:
        return None

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        return None

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        return None

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        return None

    async def upsert_price_document(
        self,
        document_id: UUID,
        external_source_id: str | None,
        label: str,
    ) -> None:
        return None

    async def upsert_price_version(
        self,
        price_version_id: UUID,
        service_id: UUID,
        document_id: UUID,
        status: str,
    ) -> None:
        return None

    async def connect_price_version_superseded(
        self,
        old_price_version_id: UUID,
        new_price_version_id: UUID,
    ) -> None:
        return None

    async def connect_raw_name_to_service(
        self,
        raw_name: str,
        partner_id: UUID,
        service_id: UUID,
        confidence: float,
        confirmed: bool,
    ) -> None:
        return None

    async def get_service_neighborhood(self, service_id: UUID, depth: int) -> GraphNeighborhood:
        return GraphNeighborhood(nodes=(), edges=())


class PostgresEdgeTableGraphRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def clear(self) -> None:
        with self._session_factory() as session:
            session.execute(delete(GraphEdgeModel))
            session.execute(delete(GraphNodeModel))
            session.commit()

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        self._upsert_node(
            GraphNode(
                node_id=_node_id("Partner", partner_id),
                node_type="Partner",
                entity_id=partner_id,
                external_id=external_partner_id,
                label=name,
                properties={"status": "active"},
            )
        )

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        self._upsert_node(
            GraphNode(
                node_id=_node_id("Service", service_id),
                node_type="Service",
                entity_id=service_id,
                external_id=external_service_id,
                label=name,
                properties={"category": category, "status": "active"},
            )
        )
        if category:
            category_id = _text_node_id("ServiceCategory", category)
            self._upsert_node(
                GraphNode(
                    node_id=category_id,
                    node_type="ServiceCategory",
                    entity_id=None,
                    external_id=None,
                    label=category,
                    properties={},
                )
            )
            self._upsert_edge(_node_id("Service", service_id), category_id, "BELONGS_TO", {})

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        self._upsert_edge(
            _node_id("Partner", partner_id),
            _node_id("Service", service_id),
            "OFFERS",
            {},
        )

    async def upsert_price_document(
        self,
        document_id: UUID,
        external_source_id: str | None,
        label: str,
    ) -> None:
        self._upsert_node(
            GraphNode(
                node_id=_node_id("PriceDocument", document_id),
                node_type="PriceDocument",
                entity_id=document_id,
                external_id=external_source_id,
                label=label,
                properties={},
            )
        )

    async def upsert_price_version(
        self,
        price_version_id: UUID,
        service_id: UUID,
        document_id: UUID,
        status: str,
    ) -> None:
        price_version_node_id = _node_id("PriceVersion", price_version_id)
        self._upsert_node(
            GraphNode(
                node_id=price_version_node_id,
                node_type="PriceVersion",
                entity_id=price_version_id,
                external_id=None,
                label=f"PriceVersion {price_version_id}",
                properties={"status": status},
            )
        )
        self._upsert_edge(
            _node_id("Service", service_id),
            price_version_node_id,
            "HAS_PRICE",
            {"status": status},
        )
        self._upsert_edge(
            price_version_node_id,
            _node_id("PriceDocument", document_id),
            "EXTRACTED_FROM",
            {},
        )

    async def connect_price_version_superseded(
        self,
        old_price_version_id: UUID,
        new_price_version_id: UUID,
    ) -> None:
        self._upsert_edge(
            _node_id("PriceVersion", old_price_version_id),
            _node_id("PriceVersion", new_price_version_id),
            "SUPERSEDED_BY",
            {},
        )

    async def connect_raw_name_to_service(
        self,
        raw_name: str,
        partner_id: UUID,
        service_id: UUID,
        confidence: float,
        confirmed: bool,
    ) -> None:
        raw_node_id = _text_node_id("RawServiceName", f"{partner_id}:{raw_name.casefold()}")
        self._upsert_node(
            GraphNode(
                node_id=raw_node_id,
                node_type="RawServiceName",
                entity_id=None,
                external_id=None,
                label=raw_name,
                properties={"partner_id": str(partner_id)},
            )
        )
        self._upsert_edge(
            raw_node_id,
            _node_id("Service", service_id),
            "CONFIRMED_AS" if confirmed else "MATCHED_TO",
            {"confidence": confidence, "confirmed": confirmed, "partner_id": str(partner_id)},
        )

    async def get_service_neighborhood(self, service_id: UUID, depth: int) -> GraphNeighborhood:
        service_node_id = _node_id("Service", service_id)
        max_depth = max(1, min(depth, 2))
        with self._session_factory() as session:
            node_ids = {service_node_id}
            frontier = {service_node_id}
            edge_rows: list[GraphEdgeModel] = []
            seen_edges: set[UUID] = set()
            for _level in range(max_depth):
                if not frontier or len(edge_rows) >= MAX_GRAPH_EDGES:
                    break
                rows = (
                    session.execute(
                        select(GraphEdgeModel)
                        .where(
                            (
                                GraphEdgeModel.source_node_id.in_(frontier)
                                | GraphEdgeModel.target_node_id.in_(frontier)
                            )
                            & GraphEdgeModel.edge_type.in_(ALLOWED_GRAPH_EDGE_TYPES)
                        )
                        .order_by(
                            GraphEdgeModel.edge_type.asc(),
                            GraphEdgeModel.source_node_id.asc(),
                            GraphEdgeModel.target_node_id.asc(),
                        )
                        .limit(MAX_GRAPH_EDGES - len(edge_rows))
                    )
                    .scalars()
                    .all()
                )
                next_frontier: set[str] = set()
                for edge in rows:
                    if edge.id in seen_edges:
                        continue
                    seen_edges.add(edge.id)
                    edge_rows.append(edge)
                    for node_id in (edge.source_node_id, edge.target_node_id):
                        if node_id not in node_ids and len(node_ids) < MAX_GRAPH_NODES:
                            node_ids.add(node_id)
                            next_frontier.add(node_id)
                frontier = next_frontier
            nodes = session.execute(
                select(GraphNodeModel).where(GraphNodeModel.node_id.in_(node_ids))
            ).scalars()
            return GraphNeighborhood(
                nodes=tuple(_node_from_model(row) for row in nodes),
                edges=tuple(
                    GraphEdge(
                        source_node_id=edge.source_node_id,
                        target_node_id=edge.target_node_id,
                        edge_type=edge.edge_type,
                        properties=edge.properties,
                    )
                    for edge in edge_rows
                ),
            )

    def _upsert_node(self, node: GraphNode) -> None:
        statement = insert(GraphNodeModel).values(
            node_id=node.node_id,
            node_type=node.node_type,
            entity_id=node.entity_id,
            external_id=node.external_id,
            label=node.label,
            properties=node.properties,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[GraphNodeModel.node_id],
            set_={
                "node_type": node.node_type,
                "entity_id": node.entity_id,
                "external_id": node.external_id,
                "label": node.label,
                "properties": node.properties,
            },
        )
        with self._session_factory() as session:
            session.execute(statement)
            session.commit()

    def _upsert_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
        properties: dict[str, object],
    ) -> None:
        if edge_type not in ALLOWED_GRAPH_EDGE_TYPES:
            raise ValueError(f"Unsupported graph edge type: {edge_type}")
        statement = insert(GraphEdgeModel).values(
            id=uuid4(),
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            properties=properties,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_graph_edges_source_target_type",
            set_={"properties": properties},
        )
        with self._session_factory() as session:
            session.execute(statement)
            session.commit()


class ApacheAgeGraphRepository(PostgresEdgeTableGraphRepository):
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        graph_name: str = "medarchive",
    ) -> None:
        super().__init__(session_factory)
        self._session_factory = session_factory
        self._graph_name = graph_name

    async def clear(self) -> None:
        await super().clear()
        self._run_cypher("MATCH (node) DETACH DELETE node", {})

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        await super().upsert_partner(partner_id, external_partner_id, name)
        self._run_cypher(
            """
            MERGE (partner:Partner {entity_id: $entity_id})
            SET partner.external_id = $external_id,
                partner.label = $label,
                partner.status = 'active'
            """,
            {"entity_id": str(partner_id), "external_id": external_partner_id, "label": name},
        )

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        await super().upsert_service(service_id, external_service_id, name, category)
        self._run_cypher(
            """
            MERGE (service:Service {entity_id: $entity_id})
            SET service.external_id = $external_id,
                service.label = $label,
                service.category = $category,
                service.status = 'active'
            """,
            {
                "entity_id": str(service_id),
                "external_id": external_service_id,
                "label": name,
                "category": category,
            },
        )

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        await super().connect_partner_service(partner_id, service_id)
        self._run_cypher(
            """
            MATCH (partner:Partner {entity_id: $partner_id})
            MATCH (service:Service {entity_id: $service_id})
            MERGE (partner)-[:OFFERS]->(service)
            """,
            {"partner_id": str(partner_id), "service_id": str(service_id)},
        )

    def _run_cypher(self, cypher: str, params: dict[str, object]) -> None:
        # AGE does not support bound Cypher parameters through every driver path consistently.
        # Keep edge tables as the guaranteed read model; AGE is deployment-enabled.
        with self._session_factory() as session:
            session.execute(text("LOAD 'age'"))
            session.execute(text('SET search_path = ag_catalog, "$user", public'))
            session.execute(
                text(
                    "SELECT * FROM cypher(:graph_name, :cypher) AS (result agtype)"
                ),
                {"graph_name": self._graph_name, "cypher": cypher},
            )
            session.commit()


def _node_id(node_type: str, entity_id: UUID) -> str:
    return f"{node_type}:{entity_id}"


def _text_node_id(node_type: str, value: str) -> str:
    return f"{node_type}:{value}"


def _node_from_model(node: GraphNodeModel) -> GraphNode:
    return GraphNode(
        node_id=node.node_id,
        node_type=node.node_type,
        entity_id=node.entity_id,
        external_id=node.external_id,
        label=node.label,
        properties=node.properties,
    )
