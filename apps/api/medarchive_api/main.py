from __future__ import annotations

from fastapi import FastAPI

from medarchive_api.observability import RequestIdMiddleware
from medarchive_api.routers.catalog_import import router as catalog_import_router
from medarchive_api.routers.evidence import router as evidence_router
from medarchive_api.routers.exports import router as exports_router
from medarchive_api.routers.graph import router as graph_router
from medarchive_api.routers.health import router as health_router
from medarchive_api.routers.ingestion import router as ingestion_router
from medarchive_api.routers.price_versions import (
    integration_router,
)
from medarchive_api.routers.price_versions import (
    router as price_versions_router,
)
from medarchive_api.routers.review_tasks import router as review_tasks_router
from medarchive_api.routers.search import router as search_router
from medarchive_api.routers.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MedArchive API",
        version="0.1.0",
        description="Integration-first production API for clinic price-list processing.",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    app.include_router(catalog_import_router, prefix="/api/v1")
    app.include_router(evidence_router, prefix="/api/v1")
    app.include_router(exports_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(integration_router, prefix="/api/v1")
    app.include_router(price_versions_router, prefix="/api/v1")
    app.include_router(review_tasks_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
    return app


app = create_app()
