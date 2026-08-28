"""
Lightweight observability: request counters/latency + a /metrics endpoint
that speaks the Prometheus text exposition format, so a real Prometheus
server can scrape this service without any other code changes.
"""

import time

from fastapi import APIRouter, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware


def _get_or_create(cls, name, *args, **kwargs):
    """
    Prometheus's default CollectorRegistry is a process-global singleton,
    so re-importing this module in the same process (module reload, test
    suites that reset sys.modules, `uvicorn --reload`) would otherwise
    raise "Duplicated timeseries". Reuse the existing collector if the
    metric name is already registered instead of crashing.
    """
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return cls(name, *args, **kwargs)


REQUEST_COUNT = _get_or_create(
    Counter,
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = _get_or_create(
    Histogram,
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

CHAT_GUARDRAIL_BLOCKS = _get_or_create(
    Counter,
    "chat_guardrail_blocks_total",
    "Number of chat messages blocked by the guardrail layer",
)

CHAT_REQUESTS = _get_or_create(
    Counter,
    "chat_requests_total",
    "Total chat requests handled",
)

CHAT_LATENCY = _get_or_create(
    Histogram,
    "chat_request_duration_seconds",
    "End-to-end chat request latency (retrieval + rerank + generation)",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Use the route template (e.g. "/documents/{document_id}") when
        # available, to avoid an unbounded label cardinality explosion.
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path

        REQUEST_COUNT.labels(
            method=request.method, path=path, status_code=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)

        return response


router = APIRouter()


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
