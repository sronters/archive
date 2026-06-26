from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class WebhookEndpoint:
    url: str
    secret: str
    enabled: bool = True


@dataclass(frozen=True)
class WebhookEvent:
    event_id: UUID
    event_type: str
    event_version: int
    payload: dict[str, object]


@dataclass(frozen=True)
class WebhookDeliveryAttempt:
    event_id: UUID
    event_type: str
    event_version: int
    endpoint_url: str
    payload: dict[str, object]
    signature: str
    status: str
    attempts: int
    response_status_code: int | None
    error: str | None
    next_attempt_at: datetime | None


@dataclass(frozen=True)
class WebhookHttpResponse:
    status_code: int
    body: str


class WebhookDeliveryRepository(Protocol):
    def record_attempt(self, attempt: WebhookDeliveryAttempt) -> None:
        ...


class WebhookHttpClient(Protocol):
    def post(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> WebhookHttpResponse:
        ...


class WebhookDispatcher:
    def __init__(
        self,
        *,
        repository: WebhookDeliveryRepository,
        http_client: WebhookHttpClient,
        max_attempts: int = 8,
    ) -> None:
        self._repository = repository
        self._http_client = http_client
        self._max_attempts = max_attempts

    def dispatch(
        self,
        *,
        event: WebhookEvent,
        endpoints: tuple[WebhookEndpoint, ...],
        attempt_number: int = 1,
    ) -> tuple[WebhookDeliveryAttempt, ...]:
        body = _canonical_body(event)
        attempts: list[WebhookDeliveryAttempt] = []
        for endpoint in endpoints:
            if not endpoint.enabled:
                continue
            signature = sign_webhook_body(body, endpoint.secret)
            headers = {
                "Content-Type": "application/json",
                "X-MedArchive-Event-Id": str(event.event_id),
                "X-MedArchive-Event-Type": event.event_type,
                "X-MedArchive-Event-Version": str(event.event_version),
                "X-MedArchive-Signature": signature,
            }
            try:
                response = self._http_client.post(url=endpoint.url, body=body, headers=headers)
                status = "delivered" if 200 <= response.status_code < 300 else "retryable"
                error = None if status == "delivered" else response.body[:1024]
                response_status = response.status_code
            except Exception as exc:
                status = "retryable"
                error = str(exc)
                response_status = None
            if status == "retryable" and attempt_number >= self._max_attempts:
                status = "dead_letter"
            attempt = WebhookDeliveryAttempt(
                event_id=event.event_id,
                event_type=event.event_type,
                event_version=event.event_version,
                endpoint_url=endpoint.url,
                payload=event.payload,
                signature=signature,
                status=status,
                attempts=attempt_number,
                response_status_code=response_status,
                error=error,
                next_attempt_at=(
                    _next_attempt(attempt_number)
                    if status == "retryable"
                    else None
                ),
            )
            self._repository.record_attempt(attempt)
            attempts.append(attempt)
        return tuple(attempts)


def sign_webhook_body(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _canonical_body(event: WebhookEvent) -> bytes:
    payload = {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "event_version": event.event_version,
        "payload": event.payload,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _next_attempt(attempt_number: int) -> datetime:
    delay_seconds = min(3600, 2 ** max(attempt_number - 1, 0))
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)  # noqa: UP017
