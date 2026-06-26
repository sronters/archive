from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from medarchive_application.catalog_import import PartnerCatalogRecord, ServiceCatalogRecord
from medarchive_application.document_processing import (
    DocumentProcessingRepository,
    DocumentToProcess,
    ExtractedItemDraft,
    ProcessingRunDraft,
)
from medarchive_application.evidence import PriceEvidence
from medarchive_application.graph_projection import PriceVersionGraphProjection
from medarchive_application.ingestion import IngestionBatchResult
from medarchive_application.ingestion_orchestrator import RecordedDocument, RecordedIngestionBatch
from medarchive_application.outbox import PendingOutboxEvent
from medarchive_application.partner_profiles import PartnerProfile, PartnerProfileDraft
from medarchive_application.price_versions import PriceVersionRead
from medarchive_application.review_preparation import (
    ExtractedItemForReview,
    ReviewDocumentContext,
    ReviewTaskDraft,
    ServiceMatchDraft,
)
from medarchive_application.review_tasks import (
    CorrectReviewTaskCommand,
    ReviewDecisionResult,
    ReviewTaskConflictError,
    ReviewTaskSummary,
)
from medarchive_application.search import PartnerSearchResult, ServiceSearchResult
from medarchive_domain.ports import GraphNeighborhood, GraphNode
from medarchive_matching.simple_matcher import CatalogService


class _FakeCatalogRecord(Protocol):
    @property
    def is_active(self) -> bool:
        ...


class FakeIngestionRecorder:
    def __init__(self) -> None:
        self.recorded_results: list[IngestionBatchResult] = []

    def record_ingestion(self, result: IngestionBatchResult) -> RecordedIngestionBatch:
        self.recorded_results.append(result)
        documents = tuple(
            RecordedDocument(
                document_id=uuid4(),
                source_file_id=uuid4(),
                original_filename=accepted.original_filename,
                storage_key=accepted.storage_key,
                detected_format=accepted.detected_format,
            )
            for accepted in result.accepted_files
        )
        return RecordedIngestionBatch(
            batch_id=result.batch_id,
            documents=documents,
            outbox_event_count=len(documents),
        )


class FakeTaskDispatcher:
    def __init__(self) -> None:
        self.dispatched_document_ids: list[UUID] = []

    async def dispatch_document_processing(self, document_id: UUID) -> None:
        self.dispatched_document_ids.append(document_id)


class FakeOutboxRepository:
    def __init__(self, events: tuple[PendingOutboxEvent, ...]) -> None:
        self.events = events
        self.processing: list[UUID] = []
        self.published: list[UUID] = []
        self.attempted: list[UUID] = []
        self.retry_errors: list[str] = []

    def list_unpublished(self, *, limit: int) -> tuple[PendingOutboxEvent, ...]:
        return self.events[:limit]

    def mark_processing(self, event_id: UUID) -> None:
        self.processing.append(event_id)

    def mark_published(self, event_id: UUID) -> None:
        self.published.append(event_id)

    def mark_retry(
        self,
        event_id: UUID,
        *,
        error: str,
        next_retry_at: datetime | None,
        max_attempts: int,
    ) -> None:
        del next_retry_at, max_attempts
        self.attempted.append(event_id)
        self.retry_errors.append(error)


class FakeDocumentProcessingRepository(DocumentProcessingRepository):
    def __init__(self, document: DocumentToProcess) -> None:
        self.document = document
        self.created_runs: list[ProcessingRunDraft] = []
        self.saved_items: list[tuple[UUID, tuple[ExtractedItemDraft, ...]]] = []
        self.statuses: list[tuple[UUID, str]] = []

    def get_document_to_process(self, document_id: UUID) -> DocumentToProcess:
        if document_id != self.document.document_id:
            raise LookupError(document_id)
        return self.document

    def create_processing_run(self, draft: ProcessingRunDraft) -> UUID:
        processing_run_id = uuid4()
        self.created_runs.append(draft)
        return processing_run_id

    def save_extracted_items(
        self,
        *,
        processing_run_id: UUID,
        items: tuple[ExtractedItemDraft, ...],
    ) -> None:
        self.saved_items.append((processing_run_id, items))

    def mark_document_status(self, *, document_id: UUID, status: str) -> None:
        self.statuses.append((document_id, status))


class FakeReviewPreparationRepository:
    def __init__(
        self,
        *,
        context: ReviewDocumentContext,
        items: tuple[ExtractedItemForReview, ...],
        catalog: tuple[CatalogService, ...],
        already_prepared: bool = False,
    ) -> None:
        self.context = context
        self.items = items
        self.catalog = catalog
        self.already_prepared = already_prepared
        self.saved_matches: tuple[ServiceMatchDraft, ...] = ()
        self.saved_tasks: tuple[ReviewTaskDraft, ...] = ()
        self.document_status: str | None = None
        self.matcher_version: str | None = None

    def get_document_context(self, processing_run_id: UUID) -> ReviewDocumentContext:
        return self.context

    def list_extracted_items(self, processing_run_id: UUID) -> tuple[ExtractedItemForReview, ...]:
        return self.items

    def list_catalog_services(self) -> tuple[CatalogService, ...]:
        return self.catalog

    def has_review_output(self, processing_run_id: UUID) -> bool:
        return self.already_prepared

    def save_review_output(
        self,
        *,
        processing_run_id: UUID,
        service_matches: tuple[ServiceMatchDraft, ...],
        review_tasks: tuple[ReviewTaskDraft, ...],
        matcher_version: str,
        document_status: str,
    ) -> None:
        self.saved_matches = service_matches
        self.saved_tasks = review_tasks
        self.matcher_version = matcher_version
        self.document_status = document_status


class FakeReviewTaskRepository:
    def __init__(self, tasks: tuple[ReviewTaskSummary, ...]) -> None:
        self.tasks = {task.task_id: task for task in tasks}
        self.price_versions: list[UUID] = []
        self.audit_events: list[UUID] = []

    def list_tasks(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[ReviewTaskSummary, ...]:
        rows = [
            task
            for task in sorted(self.tasks.values(), key=lambda item: (-item.priority, item.version))
            if status is None or task.status == status
        ]
        return tuple(rows[offset : offset + limit])

    def claim_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewTaskSummary:
        task = self.tasks[task_id]
        if task.assigned_to is not None and task.assigned_to != operator_id:
            raise ReviewTaskConflictError("Review task is already assigned.")
        claimed = replace(
            task,
            assigned_to=operator_id,
            status="claimed",
            version=task.version + 1,
        )
        self.tasks[task_id] = claimed
        return claimed

    def approve_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        task = self._decide(task_id=task_id, operator_id=operator_id, status="approved")
        price_version_id = uuid4()
        audit_event_id = uuid4()
        self.price_versions.append(price_version_id)
        self.audit_events.append(audit_event_id)
        return ReviewDecisionResult(
            task=task,
            price_version_id=price_version_id,
            audit_event_id=audit_event_id,
        )

    def reject_task(
        self,
        *,
        task_id: UUID,
        operator_id: UUID,
        reason: str,
    ) -> ReviewDecisionResult:
        task = self._decide(task_id=task_id, operator_id=operator_id, status="rejected")
        audit_event_id = uuid4()
        self.audit_events.append(audit_event_id)
        return ReviewDecisionResult(task=task, price_version_id=None, audit_event_id=audit_event_id)

    def correct_task(
        self,
        *,
        task_id: UUID,
        command: CorrectReviewTaskCommand,
    ) -> ReviewDecisionResult:
        if command.resident_price_kzt is None and command.nonresident_price_kzt is None:
            raise ValueError("At least one corrected price is required.")
        _assert_decimal(command.resident_price_kzt)
        _assert_decimal(command.nonresident_price_kzt)
        task = self._decide(task_id=task_id, operator_id=command.operator_id, status="corrected")
        price_version_id = uuid4()
        audit_event_id = uuid4()
        self.price_versions.append(price_version_id)
        self.audit_events.append(audit_event_id)
        return ReviewDecisionResult(
            task=task,
            price_version_id=price_version_id,
            audit_event_id=audit_event_id,
        )

    def release_task(self, *, task_id: UUID, operator_id: UUID) -> ReviewDecisionResult:
        task = self.tasks[task_id]
        if task.assigned_to is not None and task.assigned_to != operator_id:
            raise ReviewTaskConflictError("Review task is assigned to another operator.")
        if task.status != "claimed":
            raise ReviewTaskConflictError(f"Review task cannot be released from {task.status}.")
        released = replace(task, assigned_to=None, status="open", version=task.version + 1)
        self.tasks[task_id] = released
        audit_event_id = uuid4()
        self.audit_events.append(audit_event_id)
        return ReviewDecisionResult(
            task=released,
            price_version_id=None,
            audit_event_id=audit_event_id,
        )

    def _decide(self, *, task_id: UUID, operator_id: UUID, status: str) -> ReviewTaskSummary:
        task = self.tasks[task_id]
        if task.assigned_to is not None and task.assigned_to != operator_id:
            raise ReviewTaskConflictError("Review task is assigned to another operator.")
        if task.status not in {"open", "claimed"}:
            raise ReviewTaskConflictError(f"Review task cannot be decided from {task.status}.")
        decided = replace(
            task,
            assigned_to=operator_id,
            status=status,
            version=task.version + 1,
        )
        self.tasks[task_id] = decided
        return decided


def _assert_decimal(value: Decimal | None) -> None:
    if value is not None and not isinstance(value, Decimal):
        raise TypeError(value)


class FakePriceVersionRepository:
    def __init__(self, rows: tuple[PriceVersionRead, ...] | None = None) -> None:
        self.rows = rows or (
            PriceVersionRead(
                price_version_id=uuid4(),
                partner_id=uuid4(),
                external_partner_id="clinic-001",
                partner_name="Medical Center",
                service_id=uuid4(),
                external_service_id="svc-001",
                service_name="MRI brain",
                source_document_id=uuid4(),
                external_source_id="upload-001",
                resident_price_kzt=Decimal("25000.00"),
                nonresident_price_kzt=Decimal("32000.00"),
                original_price=Decimal("25000.00"),
                original_currency="KZT",
                exchange_rate=Decimal("1"),
                valid_from=date(2026, 6, 26),
                valid_to=None,
                published_at=datetime(2026, 6, 26, tzinfo=timezone.utc),  # noqa: UP017
                verification_status="published",
                updated_at=datetime(2026, 6, 26, tzinfo=timezone.utc),  # noqa: UP017
            ),
        )
        self.filters: dict[str, object] = {}

    def list_price_versions(
        self,
        *,
        verification_status: str | None,
        partner_id: UUID | None,
        service_id: UUID | None,
        external_partner_id: str | None,
        external_service_id: str | None,
        changed_since: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[PriceVersionRead, ...]:
        self.filters = {
            "verification_status": verification_status,
            "partner_id": partner_id,
            "service_id": service_id,
            "external_partner_id": external_partner_id,
            "external_service_id": external_service_id,
            "changed_since": changed_since,
            "limit": limit,
            "offset": offset,
        }
        return self.rows[offset : offset + limit]


class FakeCatalogImportRepository:
    def __init__(self) -> None:
        self.service_external_ids: set[str] = set()
        self.partner_external_ids: set[str] = set()
        self.applied_services: tuple[ServiceCatalogRecord, ...] = ()
        self.applied_partners: tuple[PartnerCatalogRecord, ...] = ()

    def preview_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        return _catalog_counts(records, self.service_external_ids, "external_service_id")

    def apply_services(
        self,
        records: tuple[ServiceCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        counts = self.preview_services(records)
        self.applied_services = records
        self.service_external_ids.update(record.external_service_id for record in records)
        return counts

    def preview_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
    ) -> tuple[int, int, int]:
        return _catalog_counts(records, self.partner_external_ids, "external_partner_id")

    def apply_partners(
        self,
        records: tuple[PartnerCatalogRecord, ...],
        *,
        actor_id: UUID | None,
    ) -> tuple[int, int, int]:
        counts = self.preview_partners(records)
        self.applied_partners = records
        self.partner_external_ids.update(record.external_partner_id for record in records)
        return counts


def _catalog_counts(
    records: Sequence[_FakeCatalogRecord],
    existing_external_ids: set[str],
    external_id_attr: str,
) -> tuple[int, int, int]:
    created = sum(
        1
        for record in records
        if getattr(record, external_id_attr) not in existing_external_ids
    )
    updated = len(records) - created
    deactivated = sum(1 for record in records if not record.is_active)
    return created, updated, deactivated


class FakeSearchRepository:
    def __init__(self) -> None:
        self.service_filters: dict[str, object] = {}
        self.partner_filters: dict[str, object] = {}
        self.service_id = uuid4()
        self.partner_id = uuid4()

    def search_services(
        self,
        *,
        query: str | None,
        category: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[ServiceSearchResult, ...]:
        self.service_filters = {
            "query": query,
            "category": category,
            "is_active": is_active,
            "limit": limit,
            "offset": offset,
        }
        return (
            ServiceSearchResult(
                service_id=self.service_id,
                external_service_id="svc-001",
                official_name="MRI brain",
                category="diagnostics",
                is_active=True,
            ),
        )

    def search_partners(
        self,
        *,
        query: str | None,
        city: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[PartnerSearchResult, ...]:
        self.partner_filters = {
            "query": query,
            "city": city,
            "is_active": is_active,
            "limit": limit,
            "offset": offset,
        }
        return (
            PartnerSearchResult(
                partner_id=self.partner_id,
                external_partner_id="clinic-001",
                name="Medical Center",
                bin="123456789012",
                city="Astana",
                is_active=True,
            ),
        )


class FakeEvidenceRepository:
    def __init__(self, evidence: PriceEvidence) -> None:
        self.evidence = evidence

    def get_price_evidence(self, extracted_item_id: UUID) -> PriceEvidence:
        if extracted_item_id != self.evidence.extracted_item_id:
            raise LookupError(extracted_item_id)
        return self.evidence


class FakePartnerProfileRepository:
    def __init__(self) -> None:
        self.profiles: dict[UUID, PartnerProfile] = {}

    def save_confirmed_profile(self, draft: PartnerProfileDraft) -> PartnerProfile:
        current = self.profiles.get(draft.partner_id)
        version = 1 if current is None else current.profile_version + 1
        profile = PartnerProfile(profile_version=version, **draft.__dict__)
        self.profiles[draft.partner_id] = profile
        return profile

    def get_partner_profile(self, partner_id: UUID) -> PartnerProfile | None:
        return self.profiles.get(partner_id)


class FakeGraphRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        service_id = uuid4()
        self.neighborhood = GraphNeighborhood(
            nodes=(
                GraphNode(
                    node_id=f"Service:{service_id}",
                    node_type="Service",
                    entity_id=service_id,
                    external_id="svc-001",
                    label="MRI brain",
                    properties={"category": "diagnostics"},
                ),
            ),
            edges=(),
        )

    async def clear(self) -> None:
        self.calls.append(("clear", ()))

    async def upsert_partner(
        self,
        partner_id: UUID,
        external_partner_id: str | None,
        name: str,
    ) -> None:
        self.calls.append(("upsert_partner", (partner_id, external_partner_id, name)))

    async def upsert_service(
        self,
        service_id: UUID,
        external_service_id: str | None,
        name: str,
        category: str | None,
    ) -> None:
        self.calls.append(("upsert_service", (service_id, external_service_id, name, category)))

    async def connect_partner_service(self, partner_id: UUID, service_id: UUID) -> None:
        self.calls.append(("connect_partner_service", (partner_id, service_id)))

    async def upsert_price_document(
        self,
        document_id: UUID,
        external_source_id: str | None,
        label: str,
    ) -> None:
        self.calls.append(("upsert_price_document", (document_id, external_source_id, label)))

    async def upsert_price_version(
        self,
        price_version_id: UUID,
        service_id: UUID,
        document_id: UUID,
        status: str,
    ) -> None:
        self.calls.append(
            ("upsert_price_version", (price_version_id, service_id, document_id, status))
        )

    async def connect_price_version_superseded(
        self,
        old_price_version_id: UUID,
        new_price_version_id: UUID,
    ) -> None:
        self.calls.append(
            ("connect_price_version_superseded", (old_price_version_id, new_price_version_id))
        )

    async def connect_raw_name_to_service(
        self,
        raw_name: str,
        partner_id: UUID,
        service_id: UUID,
        confidence: float,
        confirmed: bool,
    ) -> None:
        self.calls.append(
            (
                "connect_raw_name_to_service",
                (raw_name, partner_id, service_id, confidence, confirmed),
            )
        )

    async def get_service_neighborhood(self, service_id: UUID, depth: int) -> GraphNeighborhood:
        self.calls.append(("get_service_neighborhood", (service_id, depth)))
        return self.neighborhood


class FakeGraphProjectionRepository:
    def __init__(self, projection: PriceVersionGraphProjection) -> None:
        self.projection = projection

    def get_price_version_projection(
        self,
        price_version_id: UUID,
    ) -> PriceVersionGraphProjection:
        if price_version_id != self.projection.price_version_id:
            raise LookupError(price_version_id)
        return self.projection

    def list_published_price_version_ids(self) -> tuple[UUID, ...]:
        return (self.projection.price_version_id,)
