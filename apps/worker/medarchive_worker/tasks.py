from __future__ import annotations

from pathlib import Path
from uuid import UUID

from medarchive_application.document_processing import (
    DocumentProcessingResult,
    DocumentProcessingService,
)
from medarchive_application.remote_catalog_sync import (
    RemoteCatalogSyncService,
    ScheduledCatalogSyncRunner,
)
from medarchive_application.review_preparation import ReviewPreparationService
from medarchive_document_parsers.pdf_ocr import HttpOcrEngine, PdfOcrParser
from medarchive_infrastructure.catalog_import import SqlAlchemyCatalogImportRepository
from medarchive_infrastructure.document_processing import SqlAlchemyDocumentProcessingRepository
from medarchive_infrastructure.remote_catalog import (
    HttpJsonRemoteCatalogClient,
    RemoteCatalogHttpConfig,
)
from medarchive_infrastructure.review import SqlAlchemyReviewPreparationRepository
from medarchive_infrastructure.session import create_session_factory, create_sync_engine
from medarchive_infrastructure.storage import LocalFileStorage

from medarchive_worker.celery_app import celery_app
from medarchive_worker.config import get_worker_settings


@celery_app.task(name="medarchive.process_document")  # type: ignore[untyped-decorator]
def process_document(document_id: str) -> None:
    settings = get_worker_settings()
    session_factory = create_session_factory(create_sync_engine(settings.database_url))
    review_preparation = ReviewPreparationService(
        repository=SqlAlchemyReviewPreparationRepository(session_factory),
    )
    service = DocumentProcessingService(
        file_storage=LocalFileStorage(Path(settings.local_storage_root)),
        repository=SqlAlchemyDocumentProcessingRepository(session_factory),
        review_preparation_service=review_preparation,
        pdf_ocr_parser=_ocr_parser(settings.ocr_endpoint_url, settings.ocr_bearer_token),
    )
    document_uuid = UUID(document_id)
    service_result = _run_async_document_processing(service, document_uuid)
    if service_result.extracted_item_count == 0:
        raise ValueError(f"Document produced no extracted rows: {document_id}")


@celery_app.task(name="medarchive.sync_remote_catalogs")  # type: ignore[untyped-decorator]
def sync_remote_catalogs(
    service_cursor: str | None = None,
    partner_cursor: str | None = None,
) -> None:
    settings = get_worker_settings()
    session_factory = create_session_factory(create_sync_engine(settings.database_url))
    sync_service = RemoteCatalogSyncService(
        client=HttpJsonRemoteCatalogClient(
            RemoteCatalogHttpConfig(
                service_catalog_url=settings.remote_service_catalog_url,
                partner_catalog_url=settings.remote_partner_catalog_url,
                bearer_token=settings.remote_catalog_bearer_token,
            )
        ),
        repository=SqlAlchemyCatalogImportRepository(session_factory),
    )
    ScheduledCatalogSyncRunner(sync_service=sync_service).run(
        service_cursor=service_cursor,
        partner_cursor=partner_cursor,
    )


def _run_async_document_processing(
    service: DocumentProcessingService,
    document_id: UUID,
) -> DocumentProcessingResult:
    import asyncio

    return asyncio.run(service.process_document(document_id))


def _ocr_parser(endpoint_url: str | None, bearer_token: str | None) -> PdfOcrParser | None:
    if endpoint_url is None or not endpoint_url.strip():
        return None
    return PdfOcrParser(
        ocr_engine=HttpOcrEngine(endpoint_url=endpoint_url.strip(), bearer_token=bearer_token),
    )
