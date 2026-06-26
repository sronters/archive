from __future__ import annotations

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
