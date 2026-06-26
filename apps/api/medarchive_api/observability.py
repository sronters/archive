from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def prometheus_metrics_text() -> str:
    return "\n".join(
        (
            "# HELP medarchive_api_info Static API build information.",
            "# TYPE medarchive_api_info gauge",
            'medarchive_api_info{service="medarchive-api"} 1',
            "# HELP medarchive_review_queue_size Current review queue size placeholder.",
            "# TYPE medarchive_review_queue_size gauge",
            "medarchive_review_queue_size 0",
            "# HELP medarchive_webhook_failures_total Webhook delivery failures placeholder.",
            "# TYPE medarchive_webhook_failures_total counter",
            "medarchive_webhook_failures_total 0",
            "",
        )
    )
