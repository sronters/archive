from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import BinaryIO
from uuid import UUID, uuid4

import pytest
from medarchive_application.document_processing import (
    DocumentProcessingRepository,
    DocumentProcessingService,
    DocumentToProcess,
    ExtractedItemDraft,
    ProcessingRunDraft,
)
from medarchive_application.graph_projection import GraphProjector, PriceVersionGraphProjection
from medarchive_application.ingestion import (
    IngestionBatchResult,
    IngestionLimits,
    IngestionService,
    LocalNotConfiguredMalwareScanner,
)
from medarchive_application.ingestion_orchestrator import (
    RecordedDocument,
    RecordedIngestionBatch,
)
from medarchive_application.outbox import OutboxPublisher, PendingOutboxEvent
from medarchive_application.review_preparation import (
    ExtractedItemForReview,
    ReviewDocumentContext,
    ReviewPreparationRepository,
    ReviewPreparationService,
    ReviewTaskDraft,
    ServiceMatchDraft,
)
from medarchive_application.review_tasks import (
    CorrectReviewTaskCommand,
    ReviewDecisionResult,
    ReviewTaskConflictError,
    ReviewTaskService,
    ReviewTaskSummary,
)
from medarchive_domain.ports import GraphEdge, GraphNeighborhood, GraphNode
from medarchive_matching.simple_matcher import CatalogService

from tests.fakes import FakeTaskDispatcher
from tests.fixtures_xlsx import build_complex_price_xlsx


@pytest.mark.asyncio
async def test_real_xlsx_processing_publishes_price_and_projects_graph_path() -> None:
    workbook = build_complex_price_xlsx()
    storage = _MemoryStorage()
    state = _XlsxScenarioState(storage=storage)
    ingestion = IngestionService(
        file_storage=storage,
        malware_scanner=LocalNotConfiguredMalwareScanner(),
        limits=IngestionLimits(
            max_file_bytes=2_000_000,
            max_archive_file_count=10,
            max_archive_uncompressed_bytes=5_000_000,
            max_archive_compression_ratio=100,
        ),
    )

    first_batch = await ingestion.ingest_files(
        [("real-clinic-price.xlsx", workbook)],
        idempotency_key="real-price-001",
    )
    recorded = state.record_ingestion(first_batch)
    duplicate_batch = await ingestion.ingest_files(
        [("real-clinic-price.xlsx", workbook)],
        idempotency_key="real-price-001",
    )
    duplicate_recorded = state.record_ingestion(duplicate_batch)

    assert first_batch.accepted_documents_count == 1
    assert duplicate_recorded.documents[0].document_id == recorded.documents[0].document_id
    assert duplicate_recorded.outbox_event_count == 0

    processing_result = await DocumentProcessingService(
        file_storage=storage,
        repository=state,
        review_preparation_service=ReviewPreparationService(repository=state),
    ).process_document(recorded.documents[0].document_id)

    assert processing_result.extracted_item_count == 76
    assert processing_result.review_task_count == 1
    assert processing_result.status == "NEEDS_REVIEW"
    assert state.extracted_sheet_names() == {"Diagnostics", "Laboratory"}
    assert state.has_provenance_for_all_items()

    review_task = ReviewTaskService(repository=state).list_tasks(status="open")[0]
    operator_id = uuid4()
    corrected = ReviewTaskService(repository=state).correct_task(
        task_id=review_task.task_id,
        command=CorrectReviewTaskCommand(
            operator_id=operator_id,
            service_id=state.catalog[0].service_id,
            resident_price_kzt=Decimal("77777"),
            nonresident_price_kzt=Decimal("88888"),
        ),
    )

    assert corrected.price_version_id is not None
    assert len(state.price_versions) == 1
    with pytest.raises(ReviewTaskConflictError):
        ReviewTaskService(repository=state).correct_task(
            task_id=review_task.task_id,
            command=CorrectReviewTaskCommand(
                operator_id=operator_id,
                service_id=state.catalog[0].service_id,
                resident_price_kzt=Decimal("77777"),
                nonresident_price_kzt=Decimal("88888"),
            ),
        )
    assert len(state.price_versions) == 1

    graph = _InMemoryGraphRepository()
    published = await OutboxPublisher(
        repository=state,
        task_dispatcher=FakeTaskDispatcher(),
        graph_projector=GraphProjector(graph_repository=graph, projection_repository=state),
    ).publish_pending()

    assert [event.event_type for event in published] == ["price_version.published"]
    neighborhood = await graph.get_service_neighborhood(state.catalog[0].service_id, depth=2)
    node_types = {node.node_type for node in neighborhood.nodes}
    edge_types = {edge.edge_type for edge in neighborhood.edges}
    assert {"Partner", "Service", "PriceVersion", "PriceDocument"}.issubset(node_types)
    assert {"OFFERS", "HAS_PRICE", "EXTRACTED_FROM", "CONFIRMED_AS"}.issubset(edge_types)


class _MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def upload(self, key: str, content: BinaryIO, content_type: str) -> None:
        del content_type
        self.objects[key] = content.read()

    async def download(self, key: str) -> bytes:
        return self.objects[key]


@dataclass
class _ScenarioDocument:
    document_id: UUID
    source_file_id: UUID
    storage_key: str
    detected_format: str
    partner_id: UUID | None
    effective_date: date
    external_source_id: str
    status: str = "UPLOADED"


@dataclass
class _ScenarioExtractedItem:
    extracted_item_id: UUID
    processing_run_id: UUID
    sheet_name: str | None
    row_number: int | None
    service_name_raw: str
    resident_price_raw: str | None
    nonresident_price_raw: str | None
    currency_raw: str | None


@dataclass
class _ScenarioTask:
    task_id: UUID
    extracted_item_id: UUID
    reason: str
    priority: int
    status: str = "open"
    assigned_to: UUID | None = None
    version: int = 0
    price_version_id: UUID | None = None


@dataclass
class _ScenarioPriceVersion:
    price_version_id: UUID
    partner_id: UUID
    service_id: UUID
    document_id: UUID
    extracted_item_id: UUID
    status: str


class _XlsxScenarioState(DocumentProcessingRepository, ReviewPreparationRepository):
    def __init__(self, *, storage: _MemoryStorage) -> None:
        self.storage = storage
        self.partner_id = uuid4()
        self.catalog = _catalog()
        self.documents_by_sha: dict[str, RecordedDocument] = {}
        self.documents: dict[UUID, _ScenarioDocument] = {}
        self.runs: dict[UUID, UUID] = {}
        self.extracted_items: dict[UUID, _ScenarioExtractedItem] = {}
        self.matches: list[ServiceMatchDraft] = []
        self.tasks: dict[UUID, _ScenarioTask] = {}
        self.price_versions: dict[UUID, _ScenarioPriceVersion] = {}
        self.outbox_events: list[PendingOutboxEvent] = []
        self.published_events: list[UUID] = []

    def record_ingestion(self, result: IngestionBatchResult) -> RecordedIngestionBatch:
        documents: list[RecordedDocument] = []
        outbox_count = 0
        for source in result.accepted_files:
            existing = self.documents_by_sha.get(source.sha256)
            if existing is not None:
                documents.append(existing)
                continue
            document = RecordedDocument(
                document_id=uuid4(),
                source_file_id=uuid4(),
                original_filename=source.original_filename,
                storage_key=source.storage_key,
                detected_format=source.detected_format,
            )
            self.documents_by_sha[source.sha256] = document
            self.documents[document.document_id] = _ScenarioDocument(
                document_id=document.document_id,
                source_file_id=document.source_file_id,
                storage_key=document.storage_key,
                detected_format=document.detected_format,
                partner_id=self.partner_id,
                effective_date=date(2026, 6, 26),
                external_source_id="real-price-001",
            )
            documents.append(document)
            outbox_count += 1
        return RecordedIngestionBatch(
            batch_id=result.batch_id,
            documents=tuple(documents),
            outbox_event_count=outbox_count,
        )

    def get_document_to_process(self, document_id: UUID) -> DocumentToProcess:
        document = self.documents[document_id]
        return DocumentToProcess(
            document_id=document.document_id,
            detected_format=document.detected_format,
            storage_key=document.storage_key,
        )

    def create_processing_run(self, draft: ProcessingRunDraft) -> UUID:
        run_id = uuid4()
        self.runs[run_id] = draft.document_id
        return run_id

    def save_extracted_items(
        self,
        *,
        processing_run_id: UUID,
        items: tuple[ExtractedItemDraft, ...],
    ) -> None:
        for item in items:
            extracted_item_id = uuid4()
            self.extracted_items[extracted_item_id] = _ScenarioExtractedItem(
                extracted_item_id=extracted_item_id,
                processing_run_id=processing_run_id,
                sheet_name=item.sheet_name,
                row_number=item.row_number,
                service_name_raw=item.service_name_raw,
                resident_price_raw=item.resident_price_raw,
                nonresident_price_raw=item.nonresident_price_raw,
                currency_raw=item.currency_raw,
            )

    def mark_document_status(self, *, document_id: UUID, status: str) -> None:
        self.documents[document_id].status = status

    def get_document_context(self, processing_run_id: UUID) -> ReviewDocumentContext:
        document = self.documents[self.runs[processing_run_id]]
        return ReviewDocumentContext(
            document_id=document.document_id,
            partner_id=document.partner_id,
        )

    def list_extracted_items(self, processing_run_id: UUID) -> tuple[ExtractedItemForReview, ...]:
        return tuple(
            ExtractedItemForReview(
                extracted_item_id=item.extracted_item_id,
                service_name_raw=item.service_name_raw,
                resident_price_raw=item.resident_price_raw,
                nonresident_price_raw=item.nonresident_price_raw,
            )
            for item in self.extracted_items.values()
            if item.processing_run_id == processing_run_id
        )

    def list_catalog_services(self) -> tuple[CatalogService, ...]:
        return tuple(self.catalog)

    def has_review_output(self, processing_run_id: UUID) -> bool:
        return any(
            item.processing_run_id == processing_run_id
            and (
                any(match.extracted_item_id == item.extracted_item_id for match in self.matches)
                or item.extracted_item_id in {
                    task.extracted_item_id for task in self.tasks.values()
                }
            )
            for item in self.extracted_items.values()
        )

    def save_review_output(
        self,
        *,
        processing_run_id: UUID,
        service_matches: tuple[ServiceMatchDraft, ...],
        review_tasks: tuple[ReviewTaskDraft, ...],
        matcher_version: str,
        document_status: str,
    ) -> None:
        del matcher_version
        self.matches.extend(service_matches)
        for task in review_tasks:
            task_id = uuid4()
            self.tasks[task_id] = _ScenarioTask(
                task_id=task_id,
                extracted_item_id=task.extracted_item_id,
                reason=task.reason,
                priority=task.priority,
            )
        self.documents[self.runs[processing_run_id]].status = document_status

    def list_tasks(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[ReviewTaskSummary, ...]:
        rows = [
            _task_summary(task)
            for task in self.tasks.values()
            if status is None or task.status == status
        ]
        return tuple(sorted(rows, key=lambda item: -item.priority)[offset : offset + limit])

    def claim_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewTaskSummary:
        task = self.tasks[task_id]
        task.assigned_to = operator_id
        task.status = "claimed"
        task.version += 1
        return _task_summary(task)

    def approve_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        task = self.tasks[task_id]
        match = next(
            match for match in self.matches if match.extracted_item_id == task.extracted_item_id
        )
        return self._publish_task(
            task_id=task_id,
            operator_id=operator_id,
            service_id=match.service_id,
        )

    def reject_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        reason: str,
    ) -> ReviewDecisionResult:
        del reason
        task = self.tasks[task_id]
        task.status = "rejected"
        task.assigned_to = operator_id
        task.version += 1
        return ReviewDecisionResult(
            task=_task_summary(task),
            price_version_id=None,
            audit_event_id=uuid4(),
        )

    def correct_task(
        self,
        *,
        task_id: UUID,
        command: CorrectReviewTaskCommand,
    ) -> ReviewDecisionResult:
        return self._publish_task(
            task_id=task_id,
            operator_id=command.operator_id,
            service_id=command.service_id,
        )

    def release_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        task = self.tasks[task_id]
        task.assigned_to = None
        task.status = "open"
        task.version += 1
        return ReviewDecisionResult(
            task=_task_summary(task),
            price_version_id=None,
            audit_event_id=uuid4(),
        )

    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        return tuple(
            event
            for event in self.outbox_events
            if event.event_id not in self.published_events
        )[:limit]

    def mark_processing(self, event_id: UUID) -> None:
        assert event_id

    def mark_published(self, event_id: UUID) -> None:
        self.published_events.append(event_id)

    def mark_retry(
        self,
        event_id: UUID,
        *,
        error: str,
        next_retry_at: datetime | None,
        max_attempts: int,
    ) -> None:
        del event_id, error, next_retry_at, max_attempts

    def get_price_version_projection(self, price_version_id: UUID) -> PriceVersionGraphProjection:
        price_version = self.price_versions[price_version_id]
        partner_name = "Real Clinic"
        service = next(
            service for service in self.catalog if service.service_id == price_version.service_id
        )
        document = self.documents[price_version.document_id]
        extracted = self.extracted_items[price_version.extracted_item_id]
        return PriceVersionGraphProjection(
            price_version_id=price_version.price_version_id,
            partner_id=price_version.partner_id,
            external_partner_id="clinic-real-001",
            partner_name=partner_name,
            service_id=service.service_id,
            external_service_id=service.external_service_id,
            service_name=service.official_name,
            service_category=service.category,
            document_id=document.document_id,
            external_source_id=document.external_source_id,
            raw_service_name=extracted.service_name_raw,
            match_confidence=1.0,
            confirmed=True,
            status=price_version.status,
        )

    def extracted_sheet_names(self) -> set[str]:
        return {
            item.sheet_name
            for item in self.extracted_items.values()
            if item.sheet_name is not None
        }

    def has_provenance_for_all_items(self) -> bool:
        return all(item.sheet_name and item.row_number for item in self.extracted_items.values())

    def _publish_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        service_id: UUID,
    ) -> ReviewDecisionResult:
        task = self.tasks[task_id]
        if task.status not in {"open", "claimed"}:
            raise ReviewTaskConflictError(f"Review task cannot be decided from {task.status}.")
        document_id = self.runs[self.extracted_items[task.extracted_item_id].processing_run_id]
        document = self.documents[document_id]
        if document.partner_id is None:
            raise ReviewTaskConflictError("Cannot publish price without resolved partner.")
        price_version_id = uuid4()
        self.price_versions[price_version_id] = _ScenarioPriceVersion(
            price_version_id=price_version_id,
            partner_id=document.partner_id,
            service_id=service_id,
            document_id=document.document_id,
            extracted_item_id=task.extracted_item_id,
            status="published",
        )
        task.status = "corrected"
        task.assigned_to = operator_id
        task.version += 1
        task.price_version_id = price_version_id
        self.outbox_events.append(
            PendingOutboxEvent(
                event_id=uuid4(),
                event_type="price_version.published",
                event_version=1,
                payload={"price_version_id": str(price_version_id)},
            )
        )
        return ReviewDecisionResult(
            task=_task_summary(task),
            price_version_id=price_version_id,
            audit_event_id=uuid4(),
        )


class _InMemoryGraphRepository:
    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[tuple[str, str, str], GraphEdge] = {}

    async def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        self.nodes[f"Partner:{partner_id}"] = GraphNode(
            node_id=f"Partner:{partner_id}",
            node_type="Partner",
            entity_id=partner_id,
            external_id=external_partner_id,
            label=name,
            properties={},
        )

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        self.nodes[f"Service:{service_id}"] = GraphNode(
            node_id=f"Service:{service_id}",
            node_type="Service",
            entity_id=service_id,
            external_id=external_service_id,
            label=name,
            properties={"category": category},
        )

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        self._edge(f"Partner:{partner_id}", f"Service:{service_id}", "OFFERS")

    async def upsert_price_document(
        self,
        document_id: UUID,
        external_source_id: str | None,
        label: str,
    ) -> None:
        self.nodes[f"PriceDocument:{document_id}"] = GraphNode(
            node_id=f"PriceDocument:{document_id}",
            node_type="PriceDocument",
            entity_id=document_id,
            external_id=external_source_id,
            label=label,
            properties={},
        )

    async def upsert_price_version(
        self,
        price_version_id: UUID,
        service_id: UUID,
        document_id: UUID,
        status: str,
    ) -> None:
        self.nodes[f"PriceVersion:{price_version_id}"] = GraphNode(
            node_id=f"PriceVersion:{price_version_id}",
            node_type="PriceVersion",
            entity_id=price_version_id,
            external_id=None,
            label=f"PriceVersion {price_version_id}",
            properties={"status": status},
        )
        self._edge(f"Service:{service_id}", f"PriceVersion:{price_version_id}", "HAS_PRICE")
        self._edge(
            f"PriceVersion:{price_version_id}",
            f"PriceDocument:{document_id}",
            "EXTRACTED_FROM",
        )

    async def connect_price_version_superseded(
        self,
        old_price_version_id: UUID,
        new_price_version_id: UUID,
    ) -> None:
        self._edge(
            f"PriceVersion:{old_price_version_id}",
            f"PriceVersion:{new_price_version_id}",
            "SUPERSEDED_BY",
        )

    async def connect_raw_name_to_service(
        self,
        raw_name: str,
        partner_id: UUID,
        service_id: UUID,
        confidence: float,
        confirmed: bool,
    ) -> None:
        node_id = f"RawServiceName:{partner_id}:{raw_name.casefold()}"
        self.nodes[node_id] = GraphNode(
            node_id=node_id,
            node_type="RawServiceName",
            entity_id=None,
            external_id=None,
            label=raw_name,
            properties={"partner_id": str(partner_id)},
        )
        self._edge(node_id, f"Service:{service_id}", "CONFIRMED_AS" if confirmed else "MATCHED_TO")

    async def get_service_neighborhood(self, service_id: UUID, depth: int) -> GraphNeighborhood:
        del depth
        service_node_id = f"Service:{service_id}"
        connected_edges = tuple(
            edge
            for edge in self.edges.values()
            if edge.source_node_id == service_node_id or edge.target_node_id == service_node_id
        )
        price_edges = tuple(
            edge
            for edge in self.edges.values()
            if any(
                edge.source_node_id == item.target_node_id
                or edge.target_node_id == item.target_node_id
                for item in connected_edges
                if item.edge_type == "HAS_PRICE"
            )
        )
        edges = connected_edges + tuple(edge for edge in price_edges if edge not in connected_edges)
        node_ids = {service_node_id}
        for edge in edges:
            node_ids.add(edge.source_node_id)
            node_ids.add(edge.target_node_id)
        return GraphNeighborhood(
            nodes=tuple(self.nodes[node_id] for node_id in node_ids if node_id in self.nodes),
            edges=edges,
        )

    def _edge(self, source: str, target: str, edge_type: str) -> None:
        self.edges[(source, target, edge_type)] = GraphEdge(
            source_node_id=source,
            target_node_id=target,
            edge_type=edge_type,
            properties={},
        )


def _catalog() -> list[CatalogService]:
    return [
        *[
            CatalogService(
                service_id=uuid4(),
                external_service_id=f"mri-brain-{index}",
                official_name=f"MRI brain {index}",
                category="Diagnostics",
            )
            for index in range(1, 41)
        ],
        *[
            CatalogService(
                service_id=uuid4(),
                external_service_id=f"lab-test-{index}",
                official_name=f"Lab test {index}",
                category="Laboratory",
            )
            for index in range(1, 36)
        ],
    ]


def _task_summary(task: _ScenarioTask) -> ReviewTaskSummary:
    return ReviewTaskSummary(
        task_id=task.task_id,
        extracted_item_id=task.extracted_item_id,
        reason=task.reason,
        priority=task.priority,
        status=task.status,
        assigned_to=task.assigned_to,
        version=task.version,
    )
