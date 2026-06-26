from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from medarchive_application.price_diff import PriceDiffService

from tests.fakes import FakePriceVersionRepository


def test_price_diff_classifies_changed_and_anomalous_prices() -> None:
    base = FakePriceVersionRepository().rows[0]
    service_id = uuid4()
    previous = replace(
        base,
        service_id=service_id,
        external_service_id="svc-001",
        resident_price_kzt=Decimal("10000"),
    )
    current = replace(previous, resident_price_kzt=Decimal("17000"))

    diff = PriceDiffService().diff_versions(previous=(previous,), current=(current,))

    assert diff[0].status == "anomaly"
    assert diff[0].change_percent == Decimal("70.0")


def test_price_diff_classifies_new_and_removed_services() -> None:
    base = FakePriceVersionRepository().rows[0]
    removed = replace(base, service_id=uuid4(), external_service_id="removed")
    added = replace(base, service_id=uuid4(), external_service_id="added")

    diff = PriceDiffService().diff_versions(previous=(removed,), current=(added,))
    statuses = {row.external_service_id: row.status for row in diff}

    assert statuses["removed"] == "removed_service"
    assert statuses["added"] == "new_service"
