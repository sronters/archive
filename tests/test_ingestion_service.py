from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, cast
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from medarchive_application.ingestion import (
    IngestionLimits,
    IngestionService,
    LocalNotConfiguredMalwareScanner,
)
from medarchive_domain.errors import DomainErrorCode
from medarchive_infrastructure.storage import LocalFileStorage

from tests.fixtures_xlsx import build_xlsx


@pytest.mark.asyncio
async def test_ingestion_service_accepts_xlsx_and_stores_original(tmp_path: Path) -> None:
    service = IngestionService(
        file_storage=LocalFileStorage(tmp_path),
        malware_scanner=LocalNotConfiguredMalwareScanner(),
        limits=_limits(),
    )
    workbook = build_xlsx([["Название услуги", "Цена"], ["МРТ", "1000"]])

    result = await service.ingest_files([("price.xlsx", workbook)], idempotency_key="upload-1")

    assert result.accepted_documents_count == 1
    assert result.rejected_documents_count == 0
    stored = tmp_path / result.accepted_files[0].storage_key
    assert stored.exists()
    assert result.accepted_files[0].malware_scan_status == "not_configured"


@pytest.mark.asyncio
async def test_ingestion_service_accepts_non_seekable_stream(tmp_path: Path) -> None:
    service = IngestionService(
        file_storage=LocalFileStorage(tmp_path),
        malware_scanner=LocalNotConfiguredMalwareScanner(),
        limits=_limits(),
    )
    workbook = build_xlsx([["РќР°Р·РІР°РЅРёРµ СѓСЃР»СѓРіРё", "Р¦РµРЅР°"], ["РњР Рў", "1000"]])

    result = await service.ingest_file_streams(
        [("price.xlsx", cast(BinaryIO, _NonSeekableBytes(workbook)))],
        idempotency_key="upload-1",
    )

    assert result.accepted_documents_count == 1
    stored = tmp_path / result.accepted_files[0].storage_key
    assert stored.exists()


@pytest.mark.asyncio
async def test_ingestion_service_rejects_unsafe_zip_entry(tmp_path: Path) -> None:
    service = IngestionService(
        file_storage=LocalFileStorage(tmp_path),
        malware_scanner=LocalNotConfiguredMalwareScanner(),
        limits=_limits(),
    )
    archive = _zip_with_entry("../escape.xlsx", b"not really xlsx")

    result = await service.ingest_files([("bad.zip", archive)])

    assert result.accepted_documents_count == 0
    assert result.rejected_files[0].error_code == DomainErrorCode.UNSAFE_ARCHIVE_ENTRY


def _limits() -> IngestionLimits:
    return IngestionLimits(
        max_file_bytes=1024 * 1024,
        max_archive_file_count=10,
        max_archive_uncompressed_bytes=10 * 1024 * 1024,
        max_archive_compression_ratio=100,
    )


def _zip_with_entry(name: str, content: bytes) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


class _NonSeekableBytes:
    def __init__(self, content: bytes) -> None:
        self._stream = BytesIO(content)

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def seekable(self) -> bool:
        return False
