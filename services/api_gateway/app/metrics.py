"""Prometheus metrics for the API Gateway."""

from __future__ import annotations

import time
from prometheus_client import Counter, Histogram

_PROXY_REQUESTS_TOTAL = Counter(
    "gateway_proxy_requests_total",
    "Total number of proxied requests",
    ["service", "method", "status"],
)

_PROXY_LATENCY_SECONDS = Histogram(
    "gateway_proxy_upstream_latency_seconds",
    "Latency of upstream calls issued by the gateway",
    ["service", "method"],
    buckets=(
        0.01,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ),
)


def record_proxy_result(service: str, method: str, status_code: int, elapsed_seconds: float) -> None:
    """Record the result and latency of a proxied upstream call."""
    _PROXY_REQUESTS_TOTAL.labels(service=service, method=method, status=str(status_code)).inc()
    _PROXY_LATENCY_SECONDS.labels(service=service, method=method).observe(elapsed_seconds)


class TimedCall:
    """Context manager to time upstream calls and emit metrics."""

    def __init__(self, service: str, method: str) -> None:
        self.service = service
        self.method = method
        self._start = 0.0

    def __enter__(self) -> TimedCall:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        elapsed = time.perf_counter() - self._start
        status = 500 if exc_type else getattr(self, "status_code", 200)
        record_proxy_result(self.service, self.method, status, elapsed)
