from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Query
from pydantic import BaseModel


router = APIRouter(tags=["hackathon-search"])


class ServiceDemoResponse(BaseModel):
    service_id: UUID
    external_service_id: str | None
    service_name: str
    category: str | None
    is_active: bool


class PartnerDemoResponse(BaseModel):
    partner_id: UUID
    name: str
    city: str | None = None
    is_active: bool = True


class PartnerOfferDemoResponse(BaseModel):
    partner_id: UUID
    partner_name: str
    service_id: UUID
    service_name_raw: str
    price_resident_kzt: str | None
    price_nonresident_kzt: str | None
    source_file: str
    is_verified: bool


class SearchDemoResponse(BaseModel):
    kind: str
    id: str
    title: str
    subtitle: str | None = None


class UnmatchedDemoResponse(BaseModel):
    item_id: UUID
    partner_name: str
    service_name_raw: str
    review_reasons: list[str]
    source_file: str


class ManualMatchDemoRequest(BaseModel):
    item_id: UUID
    service_id: UUID
    operator_id: UUID | None = None


class ManualMatchDemoResponse(BaseModel):
    item_id: UUID
    service_id: UUID
    status: str = "accepted_for_review_demo"


@router.get("/services", response_model=list[ServiceDemoResponse])
def list_services(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ServiceDemoResponse]:
    rows = _catalog()
    if q:
        needle = _normalize(q)
        rows = [row for row in rows if needle in _normalize(str(row.get("service_name", "")))]
    if category:
        rows = [row for row in rows if _normalize(str(row.get("category", ""))) == _normalize(category)]
    return [
        ServiceDemoResponse(
            service_id=UUID(str(row["service_id"])),
            external_service_id=row.get("external_service_id"),
            service_name=str(row["service_name"]),
            category=row.get("category"),
            is_active=bool(row.get("is_active", True)),
        )
        for row in rows[offset : offset + limit]
    ]


@router.get("/services/{service_id}/partners", response_model=list[PartnerOfferDemoResponse])
def list_service_partners(
    service_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerOfferDemoResponse]:
    rows = [item for item in _items() if str(item.get("service_id")) == str(service_id)]
    return [_offer_response(item) for item in rows[offset : offset + limit]]


@router.get("/partners", response_model=list[PartnerDemoResponse])
def list_partners(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerDemoResponse]:
    names = _partner_names()
    if q:
        needle = _normalize(q)
        names = [name for name in names if needle in _normalize(name)]
    return [
        PartnerDemoResponse(partner_id=_partner_id(name), name=name)
        for name in names[offset : offset + limit]
    ]


@router.get("/partners/{partner_id}/services", response_model=list[PartnerOfferDemoResponse])
def list_partner_services(
    partner_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerOfferDemoResponse]:
    rows = [item for item in _items() if _partner_id(str(item.get("partner_name", ""))) == partner_id]
    return [_offer_response(item) for item in rows[offset : offset + limit]]


@router.get("/search", response_model=list[SearchDemoResponse])
def search(
    q: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[SearchDemoResponse]:
    needle = _normalize(q)
    results: list[SearchDemoResponse] = []
    for service in _catalog():
        name = str(service.get("service_name", ""))
        if needle in _normalize(name):
            results.append(
                SearchDemoResponse(
                    kind="service",
                    id=str(service["service_id"]),
                    title=name,
                    subtitle=str(service.get("category") or "service catalog"),
                )
            )
    for partner_name in _partner_names():
        if needle in _normalize(partner_name):
            results.append(
                SearchDemoResponse(
                    kind="partner",
                    id=str(_partner_id(partner_name)),
                    title=partner_name,
                    subtitle="partner",
                )
            )
    return results[:limit]


@router.get("/unmatched", response_model=list[UnmatchedDemoResponse])
def list_unmatched(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UnmatchedDemoResponse]:
    rows = [item for item in _items() if item.get("review_reasons")]
    return [
        UnmatchedDemoResponse(
            item_id=UUID(str(item["item_id"])),
            partner_name=str(item.get("partner_name", "")),
            service_name_raw=str(item.get("service_name_raw", "")),
            review_reasons=list(item.get("review_reasons") or []),
            source_file=str(item.get("source_file", "")),
        )
        for item in rows[offset : offset + limit]
    ]


@router.post("/match", response_model=ManualMatchDemoResponse)
def match_item(payload: ManualMatchDemoRequest) -> ManualMatchDemoResponse:
    return ManualMatchDemoResponse(item_id=payload.item_id, service_id=payload.service_id)


def _offer_response(item: dict[str, object]) -> PartnerOfferDemoResponse:
    return PartnerOfferDemoResponse(
        partner_id=_partner_id(str(item.get("partner_name", ""))),
        partner_name=str(item.get("partner_name", "")),
        service_id=UUID(str(item.get("service_id"))),
        service_name_raw=str(item.get("service_name_raw", "")),
        price_resident_kzt=str(item.get("price_resident_kzt") or "") or None,
        price_nonresident_kzt=str(item.get("price_nonresident_kzt") or "") or None,
        source_file=str(item.get("source_file", "")),
        is_verified=bool(item.get("is_verified", False)),
    )


def _partner_names() -> list[str]:
    return sorted({str(item.get("partner_name", "")) for item in _items() if item.get("partner_name")})


@lru_cache(maxsize=1)
def _catalog() -> list[dict[str, object]]:
    path = _repo_root() / "outputs" / "service_catalog_seed.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _items() -> list[dict[str, object]]:
    path = _repo_root() / "outputs" / "processed_database_preview.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("price_items") or [])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _partner_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"medarchive:partner:{_normalize(name)}")


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())
