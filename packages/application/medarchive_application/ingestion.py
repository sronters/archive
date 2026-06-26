from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, cast
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile, ZipInfo

from medarchive_domain.errors import DomainErrorCode
from medarchive_domain.ports import FileStorage, MalwareScanner

SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

COPY_CHUNK_BYTES = 1024 * 1024
SPOOL_MEMORY_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class IngestionLimits:
    max_file_bytes: int
    max_archive_file_count: int
    max_archive_uncompressed_bytes: int
    max_archive_compression_ratio: int


@dataclass(frozen=True)
class IngestedSourceFile:
    original_filename: str
    detected_mime_type: str
    detected_format: str
    size_bytes: int
    sha256: str
    storage_key: str
    malware_scan_status: str


@dataclass(frozen=True)
class RejectedSourceFile:
    original_filename: str
    error_code: DomainErrorCode
    detail: str


@dataclass(frozen=True)
class IngestionBatchResult:
    batch_id: UUID
    status: str
    accepted_files: tuple[IngestedSourceFile, ...] = ()
    rejected_files: tuple[RejectedSourceFile, ...] = ()
    links: dict[str, str] = field(default_factory=dict)

    @property
    def accepted_documents_count(self) -> int:
        return len(self.accepted_files)

    @property
    def rejected_documents_count(self) -> int:
        return len(self.rejected_files)


class LocalNotConfiguredMalwareScanner:
    async def scan(self, content: BinaryIO) -> str:
        return "not_configured"


class IngestionService:
    def __init__(
        self,
        *,
        file_storage: FileStorage,
        malware_scanner: MalwareScanner,
        limits: IngestionLimits,
    ) -> None:
        self._file_storage = file_storage
        self._malware_scanner = malware_scanner
        self._limits = limits

    async def ingest_files(
        self,
        files: list[tuple[str, bytes]],
        *,
        idempotency_key: str | None = None,
    ) -> IngestionBatchResult:
        return await self.ingest_file_streams(
            [(filename, BytesIO(content)) for filename, content in files],
            idempotency_key=idempotency_key,
        )

    async def ingest_file_streams(
        self,
        files: list[tuple[str, BinaryIO]],
        *,
        idempotency_key: str | None = None,
    ) -> IngestionBatchResult:
        batch_id = uuid4()
        accepted: list[IngestedSourceFile] = []
        rejected: list[RejectedSourceFile] = []

        for filename, stream in files:
            content = _ensure_seekable(stream)
            detected_mime = detect_mime_type_from_stream(filename=filename, content=content)
            if _looks_like_zip_archive(filename=filename, detected_mime=detected_mime):
                archive_accepted, archive_rejected = await self._ingest_zip(
                    batch_id=batch_id,
                    filename=filename,
                    content=content,
                    idempotency_key=idempotency_key,
                )
                accepted.extend(archive_accepted)
                rejected.extend(archive_rejected)
                continue

            inspected = await self._ingest_single_file(
                batch_id=batch_id,
                filename=filename,
                content=content,
                detected_mime=detected_mime,
                idempotency_key=idempotency_key,
            )
            if isinstance(inspected, IngestedSourceFile):
                accepted.append(inspected)
            else:
                rejected.append(inspected)

        status = "accepted" if not rejected else "accepted_with_rejections"
        return IngestionBatchResult(
            batch_id=batch_id,
            status=status,
            accepted_files=tuple(accepted),
            rejected_files=tuple(rejected),
            links={
                "self": f"/api/v1/ingestion-batches/{batch_id}",
                "documents": f"/api/v1/documents?batch_id={batch_id}",
            },
        )

    async def _ingest_zip(
        self,
        *,
        batch_id: UUID,
        filename: str,
        content: BinaryIO,
        idempotency_key: str | None,
    ) -> tuple[list[IngestedSourceFile], list[RejectedSourceFile]]:
        try:
            content.seek(0)
            with ZipFile(content) as archive:
                entries = [entry for entry in archive.infolist() if not entry.is_dir()]
                archive_rejection = self._validate_archive(filename, entries)
                if archive_rejection is not None:
                    return [], [archive_rejection]

                accepted: list[IngestedSourceFile] = []
                rejected: list[RejectedSourceFile] = []
                for entry in entries:
                    if _is_unsafe_archive_name(entry.filename):
                        rejected.append(
                            RejectedSourceFile(
                                original_filename=entry.filename,
                                error_code=DomainErrorCode.UNSAFE_ARCHIVE_ENTRY,
                                detail="Archive entry escapes the extraction root.",
                            )
                        )
                        continue
                    if entry.file_size > self._limits.max_file_bytes:
                        rejected.append(
                            RejectedSourceFile(
                                original_filename=entry.filename,
                                error_code=DomainErrorCode.OVERSIZED_FILE,
                                detail="Archive entry exceeds configured file size limit.",
                            )
                        )
                        continue
                    extracted = cast(BinaryIO, archive.open(entry))
                    inspected = await self._ingest_single_file(
                        batch_id=batch_id,
                        filename=entry.filename,
                        content=extracted,
                        detected_mime=None,
                        idempotency_key=idempotency_key,
                    )
                    if isinstance(inspected, IngestedSourceFile):
                        accepted.append(inspected)
                    else:
                        rejected.append(inspected)
                return accepted, rejected
        except BadZipFile:
            return [], [
                RejectedSourceFile(
                    original_filename=filename,
                    error_code=DomainErrorCode.INVALID_ARCHIVE,
                    detail="Archive cannot be opened as ZIP.",
                )
            ]

    async def _ingest_single_file(
        self,
        *,
        batch_id: UUID,
        filename: str,
        content: BinaryIO,
        detected_mime: str | None,
        idempotency_key: str | None,
    ) -> IngestedSourceFile | RejectedSourceFile:
        spooled, digest, size_bytes = _copy_to_spooled_file(
            content,
            max_bytes=self._limits.max_file_bytes,
        )
        if size_bytes > self._limits.max_file_bytes:
            return RejectedSourceFile(
                original_filename=filename,
                error_code=DomainErrorCode.OVERSIZED_FILE,
                detail="File exceeds configured size limit.",
            )

        detected_mime = detected_mime or detect_mime_type_from_stream(
            filename=filename,
            content=spooled,
        )
        detected_format = SUPPORTED_MIME_TYPES.get(detected_mime)
        if detected_format is None:
            return RejectedSourceFile(
                original_filename=filename,
                error_code=DomainErrorCode.UNSUPPORTED_FILE_TYPE,
                detail=f"Unsupported MIME type: {detected_mime}",
            )

        storage_key = _build_storage_key(
            batch_id=batch_id,
            digest=digest,
            filename=filename,
            idempotency_key=idempotency_key,
        )
        spooled.seek(0)
        malware_status = await self._malware_scanner.scan(spooled)
        spooled.seek(0)
        await self._file_storage.upload(storage_key, spooled, detected_mime)
        return IngestedSourceFile(
            original_filename=filename,
            detected_mime_type=detected_mime,
            detected_format=detected_format,
            size_bytes=size_bytes,
            sha256=digest,
            storage_key=storage_key,
            malware_scan_status=malware_status,
        )

    def _validate_archive(
        self,
        filename: str,
        entries: Iterable[ZipInfo],
    ) -> RejectedSourceFile | None:
        archive_entries = list(entries)
        if len(archive_entries) > self._limits.max_archive_file_count:
            return RejectedSourceFile(
                original_filename=filename,
                error_code=DomainErrorCode.INVALID_ARCHIVE,
                detail="Archive contains too many files.",
            )

        total_uncompressed = sum(entry.file_size for entry in archive_entries)
        total_compressed = sum(max(entry.compress_size, 1) for entry in archive_entries)
        if total_uncompressed > self._limits.max_archive_uncompressed_bytes:
            return RejectedSourceFile(
                original_filename=filename,
                error_code=DomainErrorCode.INVALID_ARCHIVE,
                detail="Archive uncompressed size exceeds configured limit.",
            )
        compression_ratio = total_uncompressed / max(total_compressed, 1)
        if compression_ratio > self._limits.max_archive_compression_ratio:
            return RejectedSourceFile(
                original_filename=filename,
                error_code=DomainErrorCode.INVALID_ARCHIVE,
                detail="Archive compression ratio exceeds configured limit.",
            )
        return None


def detect_mime_type(*, filename: str, content: bytes) -> str:
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"PK\x03\x04"):
        if _zip_contains(content, "xl/workbook.xml"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if _zip_contains(content, "word/document.xml"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/zip"
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "application/vnd.ms-excel"
    if filename.lower().endswith(".xls"):
        return "application/vnd.ms-excel"
    return "application/octet-stream"


def detect_mime_type_from_stream(*, filename: str, content: BinaryIO) -> str:
    content.seek(0)
    head = content.read(8192)
    content.seek(0)
    if head.startswith(b"PK\x03\x04"):
        if _zip_stream_contains(content, "xl/workbook.xml"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if _zip_stream_contains(content, "word/document.xml"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/zip"
    return detect_mime_type(filename=filename, content=head)


def _zip_contains(content: bytes, member_name: str) -> bool:
    try:
        with ZipFile(BytesIO(content)) as archive:
            return member_name in set(archive.namelist())
    except BadZipFile:
        return False


def _zip_stream_contains(content: BinaryIO, member_name: str) -> bool:
    try:
        content.seek(0)
        with ZipFile(content) as archive:
            return member_name in set(archive.namelist())
    except BadZipFile:
        return False
    finally:
        content.seek(0)


def _looks_like_zip_archive(*, filename: str, detected_mime: str) -> bool:
    return filename.lower().endswith(".zip") or (
        detected_mime == "application/zip"
    )


def _is_unsafe_archive_name(name: str) -> bool:
    normalized = PurePosixPath(name.replace("\\", "/"))
    return normalized.is_absolute() or ".." in normalized.parts


def _build_storage_key(
    *,
    batch_id: UUID,
    digest: str,
    filename: str,
    idempotency_key: str | None,
) -> str:
    safe_name = PurePosixPath(filename.replace("\\", "/")).name
    prefix = idempotency_key or str(batch_id)
    return f"originals/{prefix}/{digest}/{safe_name}"


def _ensure_seekable(content: BinaryIO) -> BinaryIO:
    seekable = getattr(content, "seekable", None)
    if callable(seekable) and seekable():
        content.seek(0)
        return content
    try:
        content.seek(0)
        return content
    except (AttributeError, OSError):
        pass
    spooled, _digest, _size = _copy_to_spooled_file(content, max_bytes=None)
    spooled.seek(0)
    return spooled


def _copy_to_spooled_file(
    content: BinaryIO,
    *,
    max_bytes: int | None,
) -> tuple[BinaryIO, str, int]:
    target = SpooledTemporaryFile(max_size=SPOOL_MEMORY_BYTES, mode="w+b")  # noqa: SIM115
    digest = sha256()
    size_bytes = 0
    while True:
        chunk = content.read(COPY_CHUNK_BYTES)
        if not chunk:
            break
        size_bytes += len(chunk)
        digest.update(chunk)
        target.write(chunk)
        if max_bytes is not None and size_bytes > max_bytes:
            break
    target.seek(0)
    return cast(BinaryIO, target), digest.hexdigest(), size_bytes
