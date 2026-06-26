from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from medarchive_application.search import (
    PartnerSearchResult,
    SearchRepository,
    SearchService,
    ServiceSearchResult,
)
from medarchive_infrastructure.search import SqlAlchemySearchRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class ServiceSearchResponse(BaseModel):
    service_id: UUID
    external_service_id: str | None
    official_name: str
    category: str | None
    is_active: bool


class PartnerSearchResponse(BaseModel):
    partner_id: UUID
    external_partner_id: str | None
    name: str
    bin: str | None
    city: str | None
    is_active: bool


router = APIRouter(tags=["search"])


@router.get("/services/search", response_model=list[ServiceSearchResponse])
def search_services(
    repository: Annotated[SearchRepository, Depends(get_search_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("viewer", "operator", "administrator", "integration_client")),
    ],
    query: Annotated[str | None, Query(alias="q")] = None,
    category: str | None = None,
    is_active: bool | None = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ServiceSearchResponse]:
    rows = SearchService(repository=repository).search_services(
        query=query,
        category=category,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return [_service_response(row) for row in rows]


@router.get("/partners/search", response_model=list[PartnerSearchResponse])
def search_partners(
    repository: Annotated[SearchRepository, Depends(get_search_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("viewer", "operator", "administrator", "integration_client")),
    ],
    query: Annotated[str | None, Query(alias="q")] = None,
    city: str | None = None,
    is_active: bool | None = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PartnerSearchResponse]:
    rows = SearchService(repository=repository).search_partners(
        query=query,
        city=city,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return [_partner_response(row) for row in rows]


def get_search_repository(settings: Annotated[Settings, Depends(get_settings)]) -> SearchRepository:
    return SqlAlchemySearchRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _service_response(row: ServiceSearchResult) -> ServiceSearchResponse:
    return ServiceSearchResponse(
        service_id=row.service_id,
        external_service_id=row.external_service_id,
        official_name=row.official_name,
        category=row.category,
        is_active=row.is_active,
    )


def _partner_response(row: PartnerSearchResult) -> PartnerSearchResponse:
    return PartnerSearchResponse(
        partner_id=row.partner_id,
        external_partner_id=row.external_partner_id,
        name=row.name,
        bin=row.bin,
        city=row.city,
        is_active=row.is_active,
    )
