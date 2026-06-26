from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from medarchive_application.webhooks import (
    WebhookDeliveryAttempt,
    WebhookHttpResponse,
)
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import WebhookDeliveryModel


class SqlAlchemyWebhookDeliveryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_attempt(self, attempt: WebhookDeliveryAttempt) -> None:
        with self._session_factory() as session:
            session.add(
                WebhookDeliveryModel(
                    event_id=attempt.event_id,
                    event_type=attempt.event_type,
                    event_version=attempt.event_version,
                    endpoint_url=attempt.endpoint_url,
                    payload=attempt.payload,
                    signature=attempt.signature,
                    status=attempt.status,
                    attempts=attempt.attempts,
                    response_status_code=attempt.response_status_code,
                    error=attempt.error,
                    next_attempt_at=attempt.next_attempt_at,
                )
            )
            session.commit()


class UrllibWebhookHttpClient:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def post(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> WebhookHttpResponse:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return WebhookHttpResponse(
                    status_code=response.status,
                    body=response.read().decode("utf-8", errors="replace"),
                )
        except HTTPError as exc:
            return WebhookHttpResponse(
                status_code=exc.code,
                body=exc.read().decode("utf-8", errors="replace"),
            )
        except URLError as exc:
            raise ConnectionError(str(exc.reason)) from exc
