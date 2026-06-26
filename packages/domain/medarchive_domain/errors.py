from __future__ import annotations

from enum import Enum


class DomainErrorCode(str, Enum):
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    INVALID_ARCHIVE = "invalid_archive"
    UNSAFE_ARCHIVE_ENTRY = "unsafe_archive_entry"
    OVERSIZED_FILE = "oversized_file"
    MALFORMED_DOCUMENT = "malformed_document"
    EXTRACTION_FAILURE = "extraction_failure"
    OCR_FAILURE = "ocr_failure"
    SERVICE_CATALOG_UNAVAILABLE = "service_catalog_unavailable"
    PARTNER_UNRESOLVED = "partner_unresolved"
    PUBLICATION_FAILURE = "publication_failure"
    VALIDATION_FAILURE = "validation_failure"
    DUPLICATE_UPLOAD = "duplicate_upload"
