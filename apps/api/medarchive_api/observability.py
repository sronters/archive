from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_TOTAL: dict[tuple[str, str, int], int] = defaultdict(int)
REQUEST_DURATION_BUCKETS: dict[tuple[str, str, float], int] = defaultdict(int)
REQUEST_DURATION_SUM: dict[tuple[str, str], float] = defaultdict(float)
REQUEST_DURATION_COUNT: dict[tuple[str, str], int] = defaultdict(int)
BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - started
        route = request.url.path
        method = request.method
        REQUEST_TOTAL[(method, route, response.status_code)] += 1
        REQUEST_DURATION_SUM[(method, route)] += elapsed
        REQUEST_DURATION_COUNT[(method, route)] += 1
        for bucket in BUCKETS:
            if elapsed <= bucket:
                REQUEST_DURATION_BUCKETS[(method, route, bucket)] += 1
        response.headers["X-Request-ID"] = request_id
        return response


def prometheus_metrics_text() -> str:
    lines = [
        "# HELP medarchive_api_info Static API build information.",
        "# TYPE medarchive_api_info gauge",
        'medarchive_api_info{service="medarchive-api"} 1',
        "# HELP medarchive_http_requests_total HTTP requests by method, route, and status.",
        "# TYPE medarchive_http_requests_total counter",
    ]
    for (method, route, status_code), value in sorted(REQUEST_TOTAL.items()):
        lines.append(
            "medarchive_http_requests_total"
            f'{{method="{method}",route="{route}",status_code="{status_code}"}} {value}'
        )
    lines.extend(
        (
            "# HELP medarchive_http_request_duration_seconds HTTP request duration.",
            "# TYPE medarchive_http_request_duration_seconds histogram",
        )
    )
    for method, route in sorted(REQUEST_DURATION_COUNT):
        for bucket in BUCKETS:
            bucket_count = REQUEST_DURATION_BUCKETS.get((method, route, bucket), 0)
            lines.append(
                "medarchive_http_request_duration_seconds_bucket"
                f'{{method="{method}",route="{route}",le="{bucket}"}} {bucket_count}'
            )
        count = REQUEST_DURATION_COUNT[(method, route)]
        total = REQUEST_DURATION_SUM[(method, route)]
        lines.append(
            "medarchive_http_request_duration_seconds_bucket"
            f'{{method="{method}",route="{route}",le="+Inf"}} {count}'
        )
        lines.append(
            "medarchive_http_request_duration_seconds_sum"
            f'{{method="{method}",route="{route}"}} {total:.6f}'
        )
        lines.append(
            "medarchive_http_request_duration_seconds_count"
            f'{{method="{method}",route="{route}"}} {count}'
        )
    lines.append("")
    return "\n".join(lines)
