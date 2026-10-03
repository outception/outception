"""Job runs: one row per model call or build, the operator surface beside
the health codes. `record_run` wraps a call: it opens the row as running,
closes it as completed with the served model and tokens, or as failed
with the error class and a scrubbed detail."""

from .service import (
    JobContext,
    fail_run,
    finish_run,
    mark_interrupted,
    record_run,
    start_run,
)

__all__ = [
    "JobContext",
    "fail_run",
    "finish_run",
    "mark_interrupted",
    "record_run",
    "start_run",
]
