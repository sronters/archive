from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from medarchive_application.price_versions import PriceVersionRead


@dataclass(frozen=True)
class PriceDiffRow:
    service_id: UUID
    external_service_id: str | None
    service_name: str | None
    previous_price: Decimal | None
    current_price: Decimal | None
    change_percent: Decimal | None
    status: str


class PriceDiffService:
    def diff_versions(
        self,
        *,
        previous: tuple[PriceVersionRead, ...],
        current: tuple[PriceVersionRead, ...],
        anomaly_threshold_percent: Decimal = Decimal("50"),
    ) -> tuple[PriceDiffRow, ...]:
        previous_by_service = {row.service_id: row for row in previous}
        current_by_service = {row.service_id: row for row in current}
        service_ids = sorted(
            set(previous_by_service) | set(current_by_service),
            key=lambda service_id: str(service_id),
        )
        rows: list[PriceDiffRow] = []
        for service_id in service_ids:
            previous_row = previous_by_service.get(service_id)
            current_row = current_by_service.get(service_id)
            previous_price = _business_price(previous_row)
            current_price = _business_price(current_row)
            change_percent = _change_percent(previous_price, current_price)
            status = _status(
                previous_price=previous_price,
                current_price=current_price,
                change_percent=change_percent,
                anomaly_threshold_percent=anomaly_threshold_percent,
            )
            reference = current_row or previous_row
            if reference is None:
                continue
            rows.append(
                PriceDiffRow(
                    service_id=service_id,
                    external_service_id=reference.external_service_id,
                    service_name=reference.service_name,
                    previous_price=previous_price,
                    current_price=current_price,
                    change_percent=change_percent,
                    status=status,
                )
            )
        return tuple(rows)


def _business_price(row: PriceVersionRead | None) -> Decimal | None:
    if row is None:
        return None
    return row.resident_price_kzt or row.nonresident_price_kzt


def _change_percent(
    previous_price: Decimal | None,
    current_price: Decimal | None,
) -> Decimal | None:
    if previous_price is None or current_price is None or previous_price == 0:
        return None
    return ((current_price - previous_price) / previous_price * Decimal("100")).quantize(
        Decimal("0.1")
    )


def _status(
    *,
    previous_price: Decimal | None,
    current_price: Decimal | None,
    change_percent: Decimal | None,
    anomaly_threshold_percent: Decimal,
) -> str:
    if previous_price is None and current_price is not None:
        return "new_service"
    if previous_price is not None and current_price is None:
        return "removed_service"
    if change_percent is None or change_percent == 0:
        return "unchanged"
    if abs(change_percent) >= anomaly_threshold_percent:
        return "anomaly"
    return "changed"
