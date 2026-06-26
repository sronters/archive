from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import Response

from medarchive_api.config import Settings, get_settings
from medarchive_api.observability import prometheus_metrics_text


class SystemStatusResponse(BaseModel):
    status: str
    environment: str
    auth_mode: str
    malware_scanner_mode: str
    api_namespace: str = "/api/v1"


router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemStatusResponse:
    return SystemStatusResponse(
        status="ready",
        environment=settings.environment,
        auth_mode=settings.auth_mode,
        malware_scanner_mode=settings.malware_scanner_mode,
    )


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=prometheus_metrics_text(), media_type="text/plain; version=0.0.4")
