from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PriceEvidence:
    extracted_item_id: UUID
    document_id: UUID
    source_file_id: UUID
    original_filename: str
    storage_key: str
    sha256: str
    parser_name: str
    parser_version: str
    pipeline_version: str
    processing_run_id: UUID
    page_number: int | None
    sheet_name: str | None
    row_number: int | None
    source_bbox: dict[str, float] | None
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None
    extraction_confidence: Decimal | None
    raw_payload: dict[str, object]


class EvidenceRepository(Protocol):
    def get_price_evidence(self, extracted_item_id: UUID) -> PriceEvidence:
        ...


class EvidenceService:
    def __init__(self, *, repository: EvidenceRepository) -> None:
        self._repository = repository

    def get_price_evidence(self, extracted_item_id: UUID) -> PriceEvidence:
        return self._repository.get_price_evidence(extracted_item_id)
