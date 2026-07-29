"""SLO targets for critical endpoints, exposed as Prometheus gauges so dashboards
and alert rules can join actual latency/availability against per-endpoint targets.
"""

import threading

import structlog
from prometheus_client import Gauge

log = structlog.get_logger()

SLO_P99_TARGET = Gauge(
    "outception_slo_p99_target_seconds",
    "P99 latency SLO target in seconds for critical endpoints",
    ["endpoint", "method"],
)

SLO_AVAILABILITY_TARGET = Gauge(
    "outception_slo_availability_target",
    "Availability SLO target as percentage for critical endpoints",
    ["endpoint", "method"],
)


# (route template, method, p99 target seconds, availability target percent).
# The route template must match the FastAPI route exactly, e.g. "/v1/organizations/{id}".
CRITICAL_ENDPOINTS: list[tuple[str, str, float, float]] = []

_refresh_thread: threading.Thread | None = None
_shutdown_event: threading.Event | None = None

SLO_REFRESH_INTERVAL_SECONDS = 300  # 5 minutes


def start_slo_metrics() -> None:
    """Initialize SLO metrics and start background refresh thread."""
    global _refresh_thread, _shutdown_event

    _set_slo_metrics()

    if _refresh_thread is not None:
        return

    _shutdown_event = threading.Event()
    _refresh_thread = threading.Thread(
        target=_run_refresh_loop,
        args=(_shutdown_event,),
        daemon=True,
    )
    _refresh_thread.start()
    log.info("slo_metrics_started", refresh_interval=SLO_REFRESH_INTERVAL_SECONDS)


def stop_slo_metrics() -> None:
    """Stop the SLO metrics refresh thread."""
    global _refresh_thread, _shutdown_event

    if _shutdown_event is not None:
        _shutdown_event.set()

    if _refresh_thread is not None:
        _refresh_thread.join(timeout=5.0)
        _refresh_thread = None
        _shutdown_event = None

    log.info("slo_metrics_stopped")


def _run_refresh_loop(shutdown_event: threading.Event) -> None:
    """Background loop that refreshes SLO metrics periodically."""
    while not shutdown_event.is_set():
        shutdown_event.wait(SLO_REFRESH_INTERVAL_SECONDS)
        if not shutdown_event.is_set():
            try:
                _set_slo_metrics()
            except Exception:
                log.exception("slo_metrics_refresh_error")


def _set_slo_metrics() -> None:
    """Set the gauges from CRITICAL_ENDPOINTS.

    Example alert: histogram_quantile(0.99, ...) > on(endpoint, method)
    outception_slo_p99_target_seconds
    """
    for endpoint, method, p99_target, availability_target in CRITICAL_ENDPOINTS:
        SLO_P99_TARGET.labels(endpoint=endpoint, method=method).set(p99_target)
        SLO_AVAILABILITY_TARGET.labels(endpoint=endpoint, method=method).set(
            availability_target
        )
