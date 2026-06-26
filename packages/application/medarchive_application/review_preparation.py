from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from medarchive_document_parsers.xlsx import parse_kzt_price
from medarchive_matching.simple_matcher import CatalogService, MatchCandidate, SimpleHybridMatcher


@dataclass(frozen=True)
class ExtractedItemForReview:
    extracted_item_id: UUID
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None


@dataclass(frozen=True)
class ReviewDocumentContext:
    document_id: UUID
    partner_id: UUID | None


@dataclass(frozen=True)
class ServiceMatchDraft:
    extracted_item_id: UUID
    service_id: UUID
    retrieval_method: str
    retrieval_score: Decimal
    reranker_score: Decimal | None
    matcher_version: str
    rank: int


@dataclass(frozen=True)
class ReviewTaskDraft:
    extracted_item_id: UUID
    reason: str
    priority: int


@dataclass(frozen=True)
class ReviewPreparationResult:
    processing_run_id: UUID
    matched_item_count: int
    review_task_count: int
    document_status: str


class ReviewPreparationRepository(Protocol):
    def get_document_context(self, processing_run_id: UUID) -> ReviewDocumentContext:
        ...

    def list_extracted_items(self, processing_run_id: UUID) -> tuple[ExtractedItemForReview, ...]:
        ...

    def list_catalog_services(self) -> tuple[CatalogService, ...]:
        ...

    def has_review_output(self, processing_run_id: UUID) -> bool:
        ...

    def save_review_output(
        self,
        *,
        processing_run_id: UUID,
        service_matches: tuple[ServiceMatchDraft, ...],
        review_tasks: tuple[ReviewTaskDraft, ...],
        matcher_version: str,
        document_status: str,
    ) -> None:
        ...


class ReviewPreparationService:
    def __init__(
        self,
        *,
        repository: ReviewPreparationRepository,
        matcher: SimpleHybridMatcher | None = None,
        auto_accept_threshold: float = 0.98,
    ) -> None:
        self._repository = repository
        self._matcher = matcher or SimpleHybridMatcher()
        self._auto_accept_threshold = auto_accept_threshold

    def prepare_run(self, processing_run_id: UUID) -> ReviewPreparationResult:
        if self._repository.has_review_output(processing_run_id):
            return ReviewPreparationResult(
                processing_run_id=processing_run_id,
                matched_item_count=0,
                review_task_count=0,
                document_status="unchanged",
            )

        context = self._repository.get_document_context(processing_run_id)
        catalog = list(self._repository.list_catalog_services())
        matches: list[ServiceMatchDraft] = []
        review_tasks: list[ReviewTaskDraft] = []

        for item in self._repository.list_extracted_items(processing_run_id):
            candidates = self._matcher.match(item.service_name_raw, catalog)
            accepted_service_id = _accepted_service_id(candidates, self._auto_accept_threshold)
            matches.extend(_match_drafts(item.extracted_item_id, candidates))
            reasons = _review_reasons(
                service_name=item.service_name_raw,
                resident_price=parse_kzt_price(item.resident_price_raw),
                nonresident_price=parse_kzt_price(item.nonresident_price_raw),
                accepted_service_id=accepted_service_id,
                partner_id=context.partner_id,
            )
            if reasons:
                review_tasks.append(
                    ReviewTaskDraft(
                        extracted_item_id=item.extracted_item_id,
                        reason=";".join(reasons),
                        priority=_priority_for(reasons),
                    )
                )

        document_status = "NEEDS_REVIEW" if review_tasks else "VERIFIED"
        self._repository.save_review_output(
            processing_run_id=processing_run_id,
            service_matches=tuple(matches),
            review_tasks=tuple(review_tasks),
            matcher_version=self._matcher.matcher_version,
            document_status=document_status,
        )
        return ReviewPreparationResult(
            processing_run_id=processing_run_id,
            matched_item_count=len(matches),
            review_task_count=len(review_tasks),
            document_status=document_status,
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


def _match_drafts(
    extracted_item_id: UUID,
    candidates: tuple[MatchCandidate, ...],
) -> tuple[ServiceMatchDraft, ...]:
    return tuple(
        ServiceMatchDraft(
            extracted_item_id=extracted_item_id,
            service_id=candidate.service.service_id,
            retrieval_method=candidate.retrieval_method,
            retrieval_score=Decimal(str(candidate.retrieval_score)),
            reranker_score=None,
            matcher_version=candidate.matcher_version,
            rank=candidate.rank,
        )
        for candidate in candidates
    )


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


def _priority_for(reasons: tuple[str, ...]) -> int:
    if "missing_price" in reasons or "partner_unresolved" in reasons:
        return 80
    if "service_match_uncertain" in reasons:
        return 60
    return 40
