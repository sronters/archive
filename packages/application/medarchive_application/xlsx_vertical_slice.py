from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from medarchive_document_parsers.xlsx import XlsxParser, parse_kzt_price
from medarchive_matching.simple_matcher import CatalogService, MatchCandidate, SimpleHybridMatcher


@dataclass(frozen=True)
class ValidatedPriceRow:
    source_item_id: UUID
    sheet_name: str
    row_number: int
    service_name_raw: str
    resident_price_kzt: Decimal | None
    nonresident_price_kzt: Decimal | None
    match_candidates: tuple[MatchCandidate, ...]
    accepted_service_id: UUID | None
    review_reasons: tuple[str, ...]


@dataclass(frozen=True)
class XlsxVerticalSliceResult:
    document_id: UUID
    partner_id: UUID | None
    effective_date: date | None
    rows: tuple[ValidatedPriceRow, ...]

    @property
    def review_task_count(self) -> int:
        return sum(1 for row in self.rows if row.review_reasons)

    @property
    def auto_accepted_count(self) -> int:
        return sum(1 for row in self.rows if row.accepted_service_id is not None)


class XlsxVerticalSliceProcessor:
    def __init__(
        self,
        *,
        parser: XlsxParser | None = None,
        matcher: SimpleHybridMatcher | None = None,
        auto_accept_threshold: float = 0.98,
    ) -> None:
        self._parser = parser or XlsxParser()
        self._matcher = matcher or SimpleHybridMatcher()
        self._auto_accept_threshold = auto_accept_threshold

    def process(
        self,
        *,
        workbook_content: bytes,
        catalog: list[CatalogService],
        partner_id: UUID | None = None,
        effective_date: date | None = None,
    ) -> XlsxVerticalSliceResult:
        document_id = uuid4()
        parsed = self._parser.parse(workbook_content)
        rows: list[ValidatedPriceRow] = []
        for extracted in parsed.rows:
            resident_price = parse_kzt_price(extracted.resident_price_raw)
            nonresident_price = parse_kzt_price(extracted.nonresident_price_raw)
            candidates = self._matcher.match(extracted.service_name_raw, catalog)
            accepted = _accepted_service_id(candidates, self._auto_accept_threshold)
            reasons = _review_reasons(
                service_name=extracted.service_name_raw,
                resident_price=resident_price,
                nonresident_price=nonresident_price,
                accepted_service_id=accepted,
                partner_id=partner_id,
            )
            rows.append(
                ValidatedPriceRow(
                    source_item_id=uuid4(),
                    sheet_name=extracted.sheet_name,
                    row_number=extracted.row_number,
                    service_name_raw=extracted.service_name_raw,
                    resident_price_kzt=resident_price,
                    nonresident_price_kzt=nonresident_price,
                    match_candidates=candidates,
                    accepted_service_id=accepted,
                    review_reasons=reasons,
                )
            )
        return XlsxVerticalSliceResult(
            document_id=document_id,
            partner_id=partner_id,
            effective_date=effective_date,
            rows=tuple(rows),
        )


def _accepted_service_id(
    candidates: tuple[MatchCandidate, ...],
    threshold: float,
) -> UUID | None:
    if not candidates:
        return None
    best = candidates[0]
    if best.retrieval_score >= threshold:
        return best.service.service_id
    return None


def _review_reasons(
    *,
    service_name: str,
    resident_price: Decimal | None,
    nonresident_price: Decimal | None,
    accepted_service_id: UUID | None,
    partner_id: UUID | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not service_name.strip():
        reasons.append("empty_service_name")
    if resident_price is None and nonresident_price is None:
        reasons.append("missing_price")
    if resident_price is not None and resident_price <= 0:
        reasons.append("resident_price_not_positive")
    if nonresident_price is not None and nonresident_price <= 0:
        reasons.append("nonresident_price_not_positive")
    if (
        resident_price is not None
        and nonresident_price is not None
        and nonresident_price < resident_price
    ):
        reasons.append("nonresident_price_below_resident_price")
    if accepted_service_id is None:
        reasons.append("service_match_uncertain")
    if partner_id is None:
        reasons.append("partner_unresolved")
    return tuple(reasons)
