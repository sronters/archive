from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from medarchive_api.main import create_app
from medarchive_api.routers.evidence import get_evidence_repository
from medarchive_application.evidence import PriceEvidence

from tests.fakes import FakeEvidenceRepository


def test_evidence_api_returns_source_provenance_for_extracted_price() -> None:
    extracted_item_id = uuid4()
    evidence = PriceEvidence(
        extracted_item_id=extracted_item_id,
        document_id=uuid4(),
        source_file_id=uuid4(),
        original_filename="clinic-price.pdf",
        storage_key="originals/batch/clinic-price.pdf",
        sha256="a" * 64,
        parser_name="pdf-pymupdf-text",
        parser_version="0.1.0",
        pipeline_version="document-processing-0.1.0",
        processing_run_id=uuid4(),
        page_number=17,
        sheet_name=None,
        row_number=42,
        source_bbox={"x0": 1.0, "y0": 2.0, "x1": 3.0, "y1": 4.0},
        service_name_raw="MRI brain",
        resident_price_raw="25000",
        nonresident_price_raw="32000",
        currency_raw="KZT",
        extraction_confidence=Decimal("0.984"),
        raw_payload={"source": "pdf"},
    )
    app = create_app()
    app.dependency_overrides[get_evidence_repository] = lambda: FakeEvidenceRepository(evidence)
    client = TestClient(app)

    response = client.get(
        f"/api/v1/evidence/extracted-items/{extracted_item_id}",
        headers={"X-API-Key": "dev-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_filename"] == "clinic-price.pdf"
    assert body["page_number"] == 17
    assert body["row_number"] == 42
    assert body["parser_name"] == "pdf-pymupdf-text"
    assert body["source_bbox"]["x0"] == 1.0


def test_evidence_api_is_restricted_to_operational_roles() -> None:
    app = create_app()
    app.dependency_overrides[get_evidence_repository] = lambda: FakeEvidenceRepository(
        PriceEvidence(
            extracted_item_id=uuid4(),
            document_id=uuid4(),
            source_file_id=uuid4(),
            original_filename="x.pdf",
            storage_key="x",
            sha256="a" * 64,
            parser_name="pdf",
            parser_version="1",
            pipeline_version="1",
            processing_run_id=uuid4(),
            page_number=None,
            sheet_name=None,
            row_number=None,
            source_bbox=None,
            service_name_raw="MRI",
            resident_price_raw="1",
            nonresident_price_raw=None,
            currency_raw="KZT",
            extraction_confidence=None,
            raw_payload={},
        )
    )
    client = TestClient(app)

    response = client.get(
        f"/api/v1/evidence/extracted-items/{uuid4()}",
        headers={"X-API-Key": "dev-integration"},
    )

    assert response.status_code == 403
