from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, UploadFile, status
from medarchive_application.ingestion import (
    IngestionLimits,
    IngestionService,
    LocalNotConfiguredMalwareScanner,
    RejectedSourceFile,
)
from medarchive_application.ingestion_orchestrator import IngestionOrchestrator, IngestionRecorder
from medarchive_infrastructure.ingestion_records import SqlAlchemyIngestionRecorder
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from medarchive_infrastructure.storage import LocalFileStorage
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from starlette.responses import JSONResponse

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class BatchLinks(BaseModel):
    self: str
    documents: str


class RejectedDocumentResponse(BaseModel):
    original_filename: str
    error_code: str
    detail: str


class IngestionBatchResponse(BaseModel):
    batch_id: UUID
    status: str
    accepted_documents_count: int
    rejected_documents_count: int
    links: BatchLinks
    rejected_documents: list[RejectedDocumentResponse]


router = APIRouter(prefix="/ingestion-batches", tags=["ingestion"])


@router.post("", response_model=IngestionBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_ingestion_batch(
    files: Annotated[list[UploadFile], File(description="One or more documents or ZIP archives.")],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    ingestion_recorder: Annotated[IngestionRecorder, Depends(get_ingestion_recorder)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("operator", "senior_operator", "administrator")),
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = [(upload.filename or "unnamed", upload.file) for upload in files]
    orchestrator = IngestionOrchestrator(
        ingestion_service=ingestion_service,
        ingestion_recorder=ingestion_recorder,
    )
    result, _recorded = await orchestrator.ingest_file_streams(
        payload,
        idempotency_key=idempotency_key,
    )
    response = IngestionBatchResponse(
        batch_id=result.batch_id,
        status=result.status,
        accepted_documents_count=result.accepted_documents_count,
        rejected_documents_count=result.rejected_documents_count,
        links=BatchLinks(**result.links),
        rejected_documents=[_rejected_document(rejected) for rejected in result.rejected_files],
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(mode="json"),
    )


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    return IngestionService(
        file_storage=LocalFileStorage(Path(settings.local_storage_root)),
        malware_scanner=LocalNotConfiguredMalwareScanner(),
        limits=IngestionLimits(
            max_file_bytes=settings.max_upload_file_bytes,
            max_archive_file_count=settings.max_archive_file_count,
            max_archive_uncompressed_bytes=settings.max_archive_uncompressed_bytes,
            max_archive_compression_ratio=settings.max_archive_compression_ratio,
        ),
    )


def get_ingestion_recorder(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionRecorder:
    return SqlAlchemyIngestionRecorder(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _rejected_document(rejected: RejectedSourceFile) -> RejectedDocumentResponse:
    return RejectedDocumentResponse(
        original_filename=rejected.original_filename,
        error_code=rejected.error_code.value,
        detail=rejected.detail,
    )
