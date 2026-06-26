from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from medarchive_application.evidence import EvidenceRepository, EvidenceService, PriceEvidence
from medarchive_infrastructure.evidence import SqlAlchemyEvidenceRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class PriceEvidenceResponse(BaseModel):
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


router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/extracted-items/{extracted_item_id}", response_model=PriceEvidenceResponse)
def get_extracted_item_evidence(
    extracted_item_id: UUID,
    repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator", "auditor")),
    ],
) -> PriceEvidenceResponse:
    try:
        evidence = EvidenceService(repository=repository).get_price_evidence(extracted_item_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _response(evidence)


def get_evidence_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvidenceRepository:
    return SqlAlchemyEvidenceRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _response(evidence: PriceEvidence) -> PriceEvidenceResponse:
    return PriceEvidenceResponse(**evidence.__dict__)
