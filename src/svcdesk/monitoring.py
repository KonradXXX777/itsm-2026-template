# ai-generated: 100% - Codex implemented bounded-label ASGI request instrumentation.
"""Whole-response monotonic durations; never label metrics with user input."""

from time import perf_counter
from prometheus_client import CollectorRegistry, Histogram, generate_latest

REGISTRY = CollectorRegistry()
# Measured p99=0.1248s; resolve the whole 0.08-0.24s band, not one lucky bucket.
BUCKETS = (0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.06, 0.08, 0.09, 0.1,
           0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.2, 0.22, 0.24,
           0.3, 0.4, 0.5, 0.75, 1, 2, 5)
DURATION = Histogram(
    "http_server_request_duration_seconds", "Server request duration in seconds",
    ("http_request_method", "http_route", "http_response_status_code"),
    buckets=BUCKETS, registry=REGISTRY,
)


def exposition() -> bytes:
    return generate_latest(REGISTRY)


class RequestMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/metrics":
            return await self.app(scope, receive, send)
        started = perf_counter()
        status = 500

        async def record_status(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, record_status)
        finally:
            # Starlette populates route only after routing; never use scope['path'] here.
            route = getattr(scope.get("route"), "path", "unmatched")
            method = scope["method"] if scope["method"] in {
                "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"
            } else "OTHER"
            DURATION.labels(method, route, str(status)).observe(perf_counter() - started)
