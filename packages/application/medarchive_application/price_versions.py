from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PriceVersionRead:
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


class PriceVersionRepository(Protocol):
    def list_price_versions(
        self,
        *,
        verification_status: str | None,
        partner_id: UUID | None,
        service_id: UUID | None,
        external_partner_id: str | None,
        external_service_id: str | None,
        changed_since: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[PriceVersionRead, ...]:
        ...


class PriceVersionService:
    def __init__(self, *, repository: PriceVersionRepository) -> None:
        self._repository = repository

    def list_price_versions(
        self,
        *,
        verification_status: str | None = "published",
        partner_id: UUID | None = None,
        service_id: UUID | None = None,
        external_partner_id: str | None = None,
        external_service_id: str | None = None,
        changed_since: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[PriceVersionRead, ...]:
        return self._repository.list_price_versions(
            verification_status=verification_status,
            partner_id=partner_id,
            service_id=service_id,
            external_partner_id=external_partner_id,
            external_service_id=external_service_id,
            changed_since=changed_since,
            limit=min(max(limit, 1), 200),
            offset=max(offset, 0),
        )
