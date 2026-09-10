"""HTTP request metrics for availability and latency SLIs."""

import os
from typing import TYPE_CHECKING

from outception.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp

# The multiprocess dir must exist and be exported before prometheus_client is
# imported, otherwise each API worker process keeps its own registry.
prometheus_dir = settings.WORKER_PROMETHEUS_DIR
prometheus_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", str(prometheus_dir))

from prometheus_client import (  # noqa: E402
    Counter,
    Gauge,
    Histogram,
)

# Probes and discovery endpoints: high volume, no SLO value.
METRICS_DENY_LIST: set[str] = {
    "/healthz",
    "/readyz",
    "/.well-known/openid-configuration",
    "/.well-known/jwks.json",
}

# Mounted apps excluded via exclude_app_from_metrics() (e.g. backoffice).
METRICS_EXCLUDED_APPS: set["ASGIApp"] = set()


def exclude_app_from_metrics(app: "ASGIApp") -> None:
    """Register an app to be excluded from HTTP metrics."""
    METRICS_EXCLUDED_APPS.add(app)


HTTP_REQUEST_TOTAL = Counter(
    "outception_http_request_total",
    "Total number of HTTP requests",
    ["endpoint", "method", "status_code"],
)

# Fine buckets below 0.25s for fast endpoints, coarse up to 30s for slow ones.
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "outception_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

HTTP_SSE_CONNECTIONS_OPENED = Gauge(
    "outception_http_sse_opened_connection_total",
    "Number of currently open SSE connections",
    ["endpoint"],
)
