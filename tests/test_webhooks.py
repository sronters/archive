from __future__ import annotations

from uuid import uuid4

from medarchive_application.webhooks import (
    WebhookDeliveryAttempt,
    WebhookDispatcher,
    WebhookEndpoint,
    WebhookEvent,
    WebhookHttpResponse,
    sign_webhook_body,
)


def test_webhook_dispatcher_sends_signed_payload_and_records_delivery() -> None:
    repository = _FakeWebhookDeliveryRepository()
    http_client = _FakeWebhookHttpClient(status_code=204)
    event = WebhookEvent(
        event_id=uuid4(),
        event_type="price_version.created",
        event_version=1,
        payload={"price_version_id": "pv-1"},
    )

    attempts = WebhookDispatcher(repository=repository, http_client=http_client).dispatch(
        event=event,
        endpoints=(WebhookEndpoint(url="https://example.test/webhook", secret="secret"),),
    )

    assert attempts[0].status == "delivered"
    assert repository.attempts[0].signature.startswith("sha256=")
    assert http_client.headers["X-MedArchive-Event-Type"] == "price_version.created"
    assert (
        sign_webhook_body(http_client.body, "secret")
        == http_client.headers["X-MedArchive-Signature"]
    )


def test_webhook_dispatcher_dead_letters_after_max_attempts() -> None:
    repository = _FakeWebhookDeliveryRepository()
    http_client = _FakeWebhookHttpClient(status_code=500)
    event = WebhookEvent(
        event_id=uuid4(),
        event_type="price_list.failed",
        event_version=1,
        payload={"batch_id": "batch-1"},
    )

    attempts = WebhookDispatcher(
        repository=repository,
        http_client=http_client,
        max_attempts=3,
    ).dispatch(
        event=event,
        endpoints=(WebhookEndpoint(url="https://example.test/webhook", secret="secret"),),
        attempt_number=3,
    )

    assert attempts[0].status == "dead_letter"
    assert attempts[0].next_attempt_at is None
    assert attempts[0].response_status_code == 500


class _FakeWebhookDeliveryRepository:
    def __init__(self) -> None:
        self.attempts: list[WebhookDeliveryAttempt] = []

    def record_attempt(self, attempt: WebhookDeliveryAttempt) -> None:
        self.attempts.append(attempt)


class _FakeWebhookHttpClient:
    def __init__(self, *, status_code: int) -> None:
        self._status_code = status_code
        self.body = b""
        self.headers: dict[str, str] = {}

    def post(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> WebhookHttpResponse:
        assert url == "https://example.test/webhook"
        self.body = body
        self.headers = headers
        return WebhookHttpResponse(status_code=self._status_code, body="failed")
