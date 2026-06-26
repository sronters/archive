from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from medarchive_application.exports import PriceVersionExportService
from medarchive_application.price_versions import PriceVersionRepository, PriceVersionService
from medarchive_infrastructure.price_versions import SqlAlchemyPriceVersionRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.responses import Response

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/price-versions")
def export_price_versions(
    repository: Annotated[PriceVersionRepository, Depends(get_price_version_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("integration_client", "administrator", "auditor")),
    ],
    export_format: Annotated[str, Query(pattern="^(json|csv|xlsx)$", alias="format")] = "json",
    verification_status: Annotated[str | None, Query(alias="status")] = "published",
    partner_id: UUID | None = None,
    service_id: UUID | None = None,
    external_partner_id: str | None = None,
    external_service_id: str | None = None,
    changed_since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    service = PriceVersionService(repository=repository)
    rows = service.list_price_versions(
        verification_status=verification_status,
        partner_id=partner_id,
        service_id=service_id,
        external_partner_id=external_partner_id,
        external_service_id=external_service_id,
        changed_since=changed_since,
        limit=limit,
        offset=offset,
    )
    try:
        exported = PriceVersionExportService().export_price_versions(
            rows,
            export_format=export_format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
    )


def get_price_version_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PriceVersionRepository:
    return SqlAlchemyPriceVersionRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))
