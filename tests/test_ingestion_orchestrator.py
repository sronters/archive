from __future__ import annotations

from pathlib import Path

import pytest
from medarchive_application.ingestion import (
    IngestionLimits,
    IngestionService,
    LocalNotConfiguredMalwareScanner,
)
from medarchive_application.ingestion_orchestrator import IngestionOrchestrator
from medarchive_infrastructure.storage import LocalFileStorage

from tests.fakes import FakeIngestionRecorder
from tests.fixtures_xlsx import build_xlsx


@pytest.mark.asyncio
async def test_orchestrator_records_accepted_documents_and_outbox_intent(tmp_path: Path) -> None:
    recorder = FakeIngestionRecorder()
    orchestrator = IngestionOrchestrator(
        ingestion_service=IngestionService(
            file_storage=LocalFileStorage(tmp_path),
            malware_scanner=LocalNotConfiguredMalwareScanner(),
            limits=IngestionLimits(
                max_file_bytes=1024 * 1024,
                max_archive_file_count=10,
                max_archive_uncompressed_bytes=10 * 1024 * 1024,
                max_archive_compression_ratio=100,
            ),
        ),
        ingestion_recorder=recorder,
    )
    workbook = build_xlsx([["Название услуги", "Цена"], ["МРТ", "1000"]])

    inspected, recorded = await orchestrator.ingest_files(
        [("price.xlsx", workbook)],
        idempotency_key="slice-connection",
    )

    assert inspected.accepted_documents_count == 1
    assert recorded.batch_id == inspected.batch_id
    assert len(recorded.documents) == 1
    assert recorded.outbox_event_count == 1
    assert recorder.recorded_results == [inspected]
