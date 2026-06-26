from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.graph import MAX_RESPONSE_NODES, get_graph_repository
from medarchive_domain.ports import GraphEdge, GraphNeighborhood, GraphNode

from tests.fakes import FakeGraphRepository


def test_graph_neighborhood_api_returns_cytoscape_ready_shape() -> None:
    repository = FakeGraphRepository()
    app = create_app()
    app.dependency_overrides[get_graph_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        f"/api/v1/graph/services/{uuid4()}/neighborhood?depth=2",
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nodes"][0]["type"] == "Service"
    assert body["nodes"][0]["external_id"] == "svc-001"
    assert "edges" in body
    assert body["truncated"] is False


def test_graph_neighborhood_api_requires_authorized_role() -> None:
    app = create_app()
    app.dependency_overrides[get_graph_repository] = FakeGraphRepository
    client = TestClient(app)

    response = client.get(
        f"/api/v1/graph/services/{uuid4()}/neighborhood",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 403


def test_graph_neighborhood_api_truncates_large_response() -> None:
    repository = FakeGraphRepository()
    service_id = uuid4()
    nodes = tuple(
        GraphNode(
            node_id=f"Service:{index}",
            node_type="Service",
            entity_id=service_id if index == 0 else uuid4(),
            external_id=f"svc-{index}",
            label=f"Service {index}",
            properties={},
        )
        for index in range(MAX_RESPONSE_NODES + 1)
    )
    repository.neighborhood = GraphNeighborhood(
        nodes=nodes,
        edges=(
            GraphEdge(
                source_node_id=nodes[0].node_id,
                target_node_id=nodes[1].node_id,
                edge_type="RELATED_TO",
                properties={},
            ),
        ),
    )
    app = create_app()
    app.dependency_overrides[get_graph_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        f"/api/v1/graph/services/{service_id}/neighborhood?depth=2",
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == MAX_RESPONSE_NODES
    assert body["truncated"] is True
