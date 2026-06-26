"""
Tax calculation metrics for tracking provider usage.

These metrics track which tax providers are used for calculations,
enabling monitoring of tax provider fallback behavior and usage patterns.

Metrics:
- outception_tax_calculation_total: Counter of tax calculations by provider
"""

import os

from outception.config import settings

# Setup multiprocess prometheus directory
prometheus_dir = settings.WORKER_PROMETHEUS_DIR
prometheus_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", str(prometheus_dir))

from prometheus_client import Counter  # noqa: E402

TAX_CALCULATION_TOTAL = Counter(
    "outception_tax_calculation_total",
    "Total number of tax calculations",
    ["provider", "success"],
)
