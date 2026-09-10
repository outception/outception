import os

from outception.config import settings

# Setup multiprocess prometheus directory
prometheus_dir = settings.WORKER_PROMETHEUS_DIR
prometheus_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", str(prometheus_dir))

from prometheus_client import Counter  # noqa: E402

OPERATIONAL_ERROR_TOTAL = Counter(
    "outception_operational_error_total",
    "Total number of detected operational errors",
    ["type"],
)
