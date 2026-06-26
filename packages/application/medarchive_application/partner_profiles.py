from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PartnerProfileDraft:
    partner_id: UUID
    layout_signature: str
    sheet_name: str | None
    header_row_index: int | None
    service_column: str | None
    service_code_column: str | None
    resident_price_column: str | None
    nonresident_price_column: str | None
    normalization_rules: dict[str, object]
    learned_from_document_id: UUID | None
    approved_by: UUID


@dataclass(frozen=True)
class PartnerProfile:
    partner_id: UUID
    profile_version: int
    layout_signature: str
    sheet_name: str | None
    header_row_index: int | None
    service_column: str | None
    service_code_column: str | None
    resident_price_column: str | None
    nonresident_price_column: str | None
    normalization_rules: dict[str, object]
    learned_from_document_id: UUID | None
    approved_by: UUID


class PartnerProfileRepository(Protocol):
    def save_confirmed_profile(self, draft: PartnerProfileDraft) -> PartnerProfile:
        ...

    def get_partner_profile(self, partner_id: UUID) -> PartnerProfile | None:
        ...


class PartnerProfileService:
    def __init__(self, *, repository: PartnerProfileRepository) -> None:
        self._repository = repository

    def save_confirmed_profile(self, draft: PartnerProfileDraft) -> PartnerProfile:
        if not draft.layout_signature.strip():
            raise ValueError("layout_signature is required")
        return self._repository.save_confirmed_profile(draft)

    def get_partner_profile(self, partner_id: UUID) -> PartnerProfile | None:
        return self._repository.get_partner_profile(partner_id)
