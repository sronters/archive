from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from medarchive_application.price_versions import (
    PriceVersionRead,
    PriceVersionRepository,
    PriceVersionService,
)
from medarchive_infrastructure.price_versions import SqlAlchemyPriceVersionRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class PriceVersionResponse(BaseModel):
    price_version_id: UUID
    partner_id: UUID
    external_partner_id: str | None
    partner_name: str | None
    service_id: UUID
    external_service_id: str | None
    service_name: str | None
    source_document_id: UUID
    external_source_id: str | None
    resident_price_kzt: Decimal | None
    nonresident_price_kzt: Decimal | None
    original_price: Decimal | None
    original_currency: str | None
    exchange_rate: Decimal | None
    valid_from: date
    valid_to: date | None
    published_at: datetime | None
    verification_status: str
    updated_at: datetime


router = APIRouter(prefix="/price-versions", tags=["price-versions"])
integration_router = APIRouter(tags=["price-integration"])


@router.get("", response_model=list[PriceVersionResponse])
def list_price_versions(
    repository: Annotated[PriceVersionRepository, Depends(get_price_version_repository)],
    _principal: Annotated[
        Principal,
        Depends(
            require_roles("viewer", "operator", "administrator", "auditor", "integration_client"),
        ),
    ],
    verification_status: Annotated[str | None, Query(alias="status")] = "published",
    partner_id: UUID | None = None,
    service_id: UUID | None = None,
    external_partner_id: str | None = None,
    external_service_id: str | None = None,
    changed_since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PriceVersionResponse]:
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
    return [_response(row) for row in rows]


@integration_router.get(
    "/services/{external_service_id}/offers",
    response_model=list[PriceVersionResponse],
)
def list_service_offers(
    external_service_id: str,
    repository: Annotated[PriceVersionRepository, Depends(get_price_version_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("integration_client", "administrator", "viewer")),
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PriceVersionResponse]:
    service = PriceVersionService(repository=repository)
    rows = service.list_price_versions(
        verification_status="published",
        external_service_id=external_service_id,
        limit=limit,
        offset=offset,
    )
    return [_response(row) for row in rows]


@integration_router.get(
    "/partners/{external_partner_id}/prices",
    response_model=list[PriceVersionResponse],
)
def list_partner_prices(
    external_partner_id: str,
    repository: Annotated[PriceVersionRepository, Depends(get_price_version_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("integration_client", "administrator", "viewer")),
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PriceVersionResponse]:
    service = PriceVersionService(repository=repository)
    rows = service.list_price_versions(
        verification_status="published",
        external_partner_id=external_partner_id,
        limit=limit,
        offset=offset,
    )
    return [_response(row) for row in rows]


@integration_router.get("/price-changes", response_model=list[PriceVersionResponse])
def list_price_changes(
    repository: Annotated[PriceVersionRepository, Depends(get_price_version_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("integration_client", "administrator", "viewer")),
    ],
    changed_since: datetime,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PriceVersionResponse]:
    service = PriceVersionService(repository=repository)
    rows = service.list_price_versions(
        verification_status="published",
        changed_since=changed_since,
        limit=limit,
        offset=offset,
    )
    return [_response(row) for row in rows]


def get_price_version_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PriceVersionRepository:
    return SqlAlchemyPriceVersionRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _response(row: PriceVersionRead) -> PriceVersionResponse:
    return PriceVersionResponse(
        price_version_id=row.price_version_id,
        partner_id=row.partner_id,
        external_partner_id=row.external_partner_id,
        partner_name=row.partner_name,
        service_id=row.service_id,
        external_service_id=row.external_service_id,
        service_name=row.service_name,
        source_document_id=row.source_document_id,
        external_source_id=row.external_source_id,
        resident_price_kzt=row.resident_price_kzt,
        nonresident_price_kzt=row.nonresident_price_kzt,
        original_price=row.original_price,
        original_currency=row.original_currency,
        exchange_rate=row.exchange_rate,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        published_at=row.published_at,
        verification_status=row.verification_status,
        updated_at=row.updated_at,
    )
