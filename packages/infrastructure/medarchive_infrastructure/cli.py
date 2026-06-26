from __future__ import annotations

import argparse
import asyncio
import os

from medarchive_application.graph_projection import GraphProjector
from medarchive_application.graph_rebuild import GraphRebuilder, GraphRebuildResult
from medarchive_domain.ports import GraphRepository
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.graph import (
    ApacheAgeGraphRepository,
    NoOpGraphRepository,
    PostgresEdgeTableGraphRepository,
)
from medarchive_infrastructure.graph_projection import SqlAlchemyGraphProjectionRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine


def main() -> None:
    parser = argparse.ArgumentParser(prog="medarchive")
    subparsers = parser.add_subparsers(dest="command", required=True)
    graph_parser = subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)
    graph_subparsers.add_parser("rebuild")
    args = parser.parse_args()

    if args.command == "graph" and args.graph_command == "rebuild":
        result = asyncio.run(_rebuild_graph())
        print(f"projected_price_versions={result.projected_price_versions}")


async def _rebuild_graph() -> GraphRebuildResult:
    database_url = _required_env("DATABASE_URL")
    graph_backend = os.getenv("GRAPH_BACKEND", "postgres_edges")
    graph_name = os.getenv("GRAPH_NAME", "medarchive")
    session_factory = create_session_factory(create_sync_engine(database_url))
    projection_repository = SqlAlchemyGraphProjectionRepository(session_factory)
    graph_repository = _graph_repository(
        backend=graph_backend,
        graph_name=graph_name,
        session_factory=session_factory,
    )
    projector = GraphProjector(
        graph_repository=graph_repository,
        projection_repository=projection_repository,
    )
    return await GraphRebuilder(
        graph_repository=graph_repository,
        projection_repository=projection_repository,
        projector=projector,
    ).rebuild()


def _graph_repository(
    *,
    backend: str,
    graph_name: str,
    session_factory: sessionmaker[Session],
) -> GraphRepository:
    if backend == "noop":
        return NoOpGraphRepository()
    if backend == "apache_age":
        return ApacheAgeGraphRepository(session_factory, graph_name=graph_name)
    if backend == "postgres_edges":
        return PostgresEdgeTableGraphRepository(session_factory)
    raise ValueError(f"Unsupported GRAPH_BACKEND: {backend}")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
