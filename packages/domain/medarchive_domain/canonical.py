from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class ExtractionConfidence:
    value: float | None
    method: str | None = None

    def __post_init__(self) -> None:
        if self.value is not None and not 0 <= self.value <= 1:
            raise ValueError("confidence value must be between 0 and 1")


@dataclass(frozen=True)
class ParserMetadata:
    parser_name: str
    parser_version: str
    pipeline_version: str


@dataclass(frozen=True)
class SourceProvenance:
    source_document_id: UUID
    processing_run_id: UUID
    parser_name: str
    parser_version: str
    page_number: int | None = None
    sheet_name: str | None = None
    row_number: int | None = None
    bounding_box: BoundingBox | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TextBlock:
    text: str
    bbox: BoundingBox | None
    confidence: ExtractionConfidence


@dataclass(frozen=True)
class TableCell:
    row_index: int
    column_index: int
    text: str
    bbox: BoundingBox | None
    confidence: ExtractionConfidence
    row_span: int = 1
    column_span: int = 1


@dataclass(frozen=True)
class TableRow:
    row_index: int
    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class TableBlock:
    rows: tuple[TableRow, ...]
    bbox: BoundingBox | None = None


@dataclass(frozen=True)
class CanonicalPage:
    page_number: int
    width: float | None
    height: float | None
    blocks: tuple[TextBlock, ...] = ()
    tables: tuple[TableBlock, ...] = ()


@dataclass(frozen=True)
class CanonicalDocument:
    document_id: UUID
    metadata: ParserMetadata
    pages: tuple[CanonicalPage, ...] = ()
    document_metadata: dict[str, str] = field(default_factory=dict)
