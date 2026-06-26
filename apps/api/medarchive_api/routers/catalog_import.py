from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from medarchive_application.catalog_import import (
    CatalogImportIssue,
    CatalogImportReport,
    CatalogImportRepository,
    CatalogImportService,
)
from medarchive_infrastructure.catalog_import import SqlAlchemyCatalogImportRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medarchive_api.config import Settings, get_settings
from medarchive_api.security import Principal, require_roles


class CatalogImportIssueResponse(BaseModel):
    row_number: int
    external_id: str | None
    code: str
    detail: str


class CatalogImportReportResponse(BaseModel):
    mode: str
    entity_type: str
    total_rows: int
    valid_rows: int
    created_count: int
    updated_count: int
    deactivated_count: int
    issues: list[CatalogImportIssueResponse]


router = APIRouter(tags=["catalog-import"])


@router.post("/service-catalog/imports", response_model=CatalogImportReportResponse)
async def import_service_catalog(
    repository: Annotated[CatalogImportRepository, Depends(get_catalog_import_repository)],
    _principal: Annotated[Principal, Depends(require_roles("catalog_manager", "administrator"))],
    file: Annotated[UploadFile, File(description="JSON service catalog file.")],
    mode: Annotated[str, Form(pattern="^(preview|apply)$")] = "preview",
    actor_id: Annotated[UUID | None, Form()] = None,
) -> CatalogImportReportResponse:
    content = await file.read()
    service = CatalogImportService(repository=repository)
    try:
        report = (
            service.preview_services(content)
            if mode == "preview"
            else service.apply_services(content, actor_id=actor_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _report_response(report)


@router.post("/partners/imports", response_model=CatalogImportReportResponse)
async def import_partners(
    repository: Annotated[CatalogImportRepository, Depends(get_catalog_import_repository)],
    _principal: Annotated[Principal, Depends(require_roles("catalog_manager", "administrator"))],
    file: Annotated[UploadFile, File(description="JSON partner catalog file.")],
    mode: Annotated[str, Form(pattern="^(preview|apply)$")] = "preview",
    actor_id: Annotated[UUID | None, Form()] = None,
) -> CatalogImportReportResponse:
    content = await file.read()
    service = CatalogImportService(repository=repository)
    try:
        report = (
            service.preview_partners(content)
            if mode == "preview"
            else service.apply_partners(content, actor_id=actor_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _report_response(report)


def get_catalog_import_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogImportRepository:
    return SqlAlchemyCatalogImportRepository(_session_factory(settings.database_url))


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_sync_engine(database_url))


def _report_response(report: CatalogImportReport) -> CatalogImportReportResponse:
    return CatalogImportReportResponse(
        mode=report.mode,
        entity_type=report.entity_type,
        total_rows=report.total_rows,
        valid_rows=report.valid_rows,
        created_count=report.created_count,
        updated_count=report.updated_count,
        deactivated_count=report.deactivated_count,
        issues=[_issue_response(issue) for issue in report.issues],
    )


def _issue_response(issue: CatalogImportIssue) -> CatalogImportIssueResponse:
    return CatalogImportIssueResponse(
        row_number=issue.row_number,
        external_id=issue.external_id,
        code=issue.code,
        detail=issue.detail,
    )
