from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import UUID


@dataclass(frozen=True)
class CatalogService:
    service_id: UUID
    official_name: str
    external_service_id: str | None = None
    synonyms: tuple[str, ...] = ()
    category: str | None = None


@dataclass(frozen=True)
class MatchCandidate:
    service: CatalogService
    retrieval_method: str
    retrieval_score: float
    rank: int
    matcher_version: str = "simple-hybrid-0.1.0"


class SimpleHybridMatcher:
    matcher_version = "simple-hybrid-0.2.0"

    def match(
        self,
        raw_service_name: str,
        catalog: list[CatalogService],
    ) -> tuple[MatchCandidate, ...]:
        normalized_raw = normalize_service_text(raw_service_name)
        candidates: list[MatchCandidate] = []
        for service in catalog:
            if service.external_service_id is not None and normalized_raw == normalize_service_text(
                service.external_service_id,
            ):
                candidates.append(
                    MatchCandidate(
                        service=service,
                        retrieval_method="source_code",
                        retrieval_score=1.0,
                        rank=0,
                        matcher_version=self.matcher_version,
                    )
                )
                continue
            names = (service.official_name, *service.synonyms)
            best_method = "fuzzy"
            best_score = 0.0
            for name in names:
                normalized_name = normalize_service_text(name)
                if normalized_raw == normalized_name:
                    method = "exact_name" if name == service.official_name else "exact_synonym"
                    score = 1.0
                else:
                    method = "fuzzy"
                    score = SequenceMatcher(None, normalized_raw, normalized_name).ratio()
                if score > best_score:
                    best_method = method
                    best_score = score
            if best_score > 0:
                candidates.append(
                    MatchCandidate(
                        service=service,
                        retrieval_method=best_method,
                        retrieval_score=best_score,
                        rank=0,
                        matcher_version=self.matcher_version,
                    )
                )
        ranked = sorted(candidates, key=lambda candidate: candidate.retrieval_score, reverse=True)
        return tuple(
            MatchCandidate(
                service=candidate.service,
                retrieval_method=candidate.retrieval_method,
                retrieval_score=candidate.retrieval_score,
                rank=index + 1,
                matcher_version=self.matcher_version,
            )
            for index, candidate in enumerate(ranked[:10])
        )


def normalize_service_text(value: str) -> str:
    normalized = value.casefold().replace("ё", "е")
    for char in (".", ",", ";", ":", "(", ")", "[", "]", "{", "}", "\"", "'"):
        normalized = normalized.replace(char, " ")
    return " ".join(normalized.split())
