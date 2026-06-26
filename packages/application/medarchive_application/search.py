from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ServiceSearchResult:
    service_id: UUID
    external_service_id: str | None
    official_name: str
    category: str | None
    is_active: bool


@dataclass(frozen=True)
class PartnerSearchResult:
    partner_id: UUID
    external_partner_id: str | None
    name: str
    bin: str | None
    city: str | None
    is_active: bool


class SearchRepository(Protocol):
    def search_services(
        self,
        *,
        query: str | None,
        category: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[ServiceSearchResult, ...]:
        ...

    def search_partners(
        self,
        *,
        query: str | None,
        city: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[PartnerSearchResult, ...]:
        ...


class SearchService:
    def __init__(self, *, repository: SearchRepository) -> None:
        self._repository = repository

    def search_services(
        self,
        *,
        query: str | None,
        category: str | None = None,
        is_active: bool | None = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[ServiceSearchResult, ...]:
        return self._repository.search_services(
            query=_clean(query),
            category=_clean(category),
            is_active=is_active,
            limit=min(max(limit, 1), 200),
            offset=max(offset, 0),
        )

    def search_partners(
        self,
        *,
        query: str | None,
        city: str | None = None,
        is_active: bool | None = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[PartnerSearchResult, ...]:
        return self._repository.search_partners(
            query=_clean(query),
            city=_clean(city),
            is_active=is_active,
            limit=min(max(limit, 1), 200),
            offset=max(offset, 0),
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
