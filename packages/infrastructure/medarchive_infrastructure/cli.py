from __future__ import annotations

import argparse
import asyncio
import json
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import httpx
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

SUPPORTED_UPLOAD_EXTENSIONS = {".docx", ".pdf", ".xls", ".xlsx", ".zip"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="medarchive")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Загрузить документ, ZIP или папку документов в MedArchive API.",
    )
    ingest_parser.add_argument("path", type=Path)
    ingest_parser.add_argument(
        "--api-url",
        default=os.getenv("MEDARCHIVE_API_URL", "http://localhost:8000"),
    )
    ingest_parser.add_argument(
        "--api-key",
        default=os.getenv("MEDARCHIVE_API_KEY", "dev-admin"),
    )
    ingest_parser.add_argument("--idempotency-key")

    graph_parser = subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)
    graph_subparsers.add_parser("rebuild")
    args = parser.parse_args(argv)

    if args.command == "ingest":
        paths = _upload_paths(args.path)
        upload_result = _upload_files(
            paths=paths,
            api_url=args.api_url,
            api_key=args.api_key,
            idempotency_key=args.idempotency_key,
        )
        print(json.dumps(upload_result, ensure_ascii=False, indent=2))
    elif args.command == "graph" and args.graph_command == "rebuild":
        graph_result = asyncio.run(_rebuild_graph())
        print(f"projected_price_versions={graph_result.projected_price_versions}")


def _upload_paths(path: Path) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(f"Путь не найден: {path}")
    if path.is_file():
        candidates = [path]
    else:
        candidates = sorted(item for item in path.iterdir() if item.is_file())
    supported = [item for item in candidates if item.suffix.lower() in SUPPORTED_UPLOAD_EXTENSIONS]
    if not supported:
        raise ValueError("Не найдены файлы ZIP, PDF, DOCX, XLS или XLSX.")
    return supported


def _upload_files(
    *,
    paths: list[Path],
    api_url: str,
    api_key: str,
    idempotency_key: str | None,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    with ExitStack() as stack:
        files = [
            (
                "files",
                (
                    path.name,
                    stack.enter_context(path.open("rb")),
                    "application/octet-stream",
                ),
            )
            for path in paths
        ]
        response = httpx.post(
            f"{api_url.rstrip('/')}/api/v1/ingestion-batches",
            files=files,
            headers=headers,
            timeout=120,
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("API вернул неожиданный формат ответа.")
    return payload


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
