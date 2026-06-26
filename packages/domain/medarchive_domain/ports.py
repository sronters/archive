from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import BinaryIO, Protocol
from uuid import UUID

from medarchive_domain.entities import Partner, Service


class FileStorage(Protocol):
    async def upload(self, key: str, content: BinaryIO, content_type: str) -> None:
        ...

    async def download(self, key: str) -> bytes:
        ...


class TaskDispatcher(Protocol):
    async def dispatch_document_processing(self, document_id: UUID) -> None:
        ...


class PartnerProvider(Protocol):
    async def resolve_partner(
        self,
        *,
        external_partner_id: str | None,
        name: str | None,
        bin: str | None,
    ) -> Partner | None:
        ...


class ServiceCatalogProvider(Protocol):
    async def list_active_services(self) -> list[Service]:
        ...

    async def get_by_external_id(self, external_service_id: str) -> Service | None:
        ...


class PublicationPublisher(Protocol):
    async def publish_price_list_published(self, document_id: UUID) -> None:
        ...


class IdentityProvider(Protocol):
    async def authenticate(self, token: str) -> object:
        ...


class ExchangeRateProvider(Protocol):
    async def get_rate_to_kzt(self, currency: str, rate_date: date) -> Decimal:
        ...


class MalwareScanner(Protocol):
    async def scan(self, content: BinaryIO) -> str:
        ...


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    entity_id: UUID | None
    external_id: str | None
    label: str
    properties: dict[str, object]


@dataclass(frozen=True)
class GraphEdge:
    source_node_id: str
    target_node_id: str
    edge_type: str
    properties: dict[str, object]


@dataclass(frozen=True)
class GraphNeighborhood:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


class GraphRepository(Protocol):
    async def clear(self) -> None:
        ...

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        ...

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        ...

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        ...

    async def upsert_price_document(
        self,
        document_id: UUID,
        external_source_id: str | None,
        label: str,
    ) -> None:
        ...

    async def upsert_price_version(
        self,
        price_version_id: UUID,
        service_id: UUID,
        document_id: UUID,
        status: str,
    ) -> None:
        ...

    async def connect_price_version_superseded(
        self,
        old_price_version_id: UUID,
        new_price_version_id: UUID,
    ) -> None:
        ...

    async def connect_raw_name_to_service(
        self,
        raw_name: str,
        partner_id: UUID,
        service_id: UUID,
        confidence: float,
        confirmed: bool,
    ) -> None:
        ...

    async def get_service_neighborhood(
        self,
        service_id: UUID,
        depth: int,
    ) -> GraphNeighborhood:
        ...
