"""Health reason codes: stable snake_case codes with a severity and a remedy,
read by `/health`, the healthcheck alert and the health skill. Health reads
only observe state; they never trigger work."""

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


@dataclass(frozen=True)
class ReasonSpec:
    code: str
    subsystem: str
    severity: Severity
    remedy: str


REASONS: dict[str, ReasonSpec] = {
    spec.code: spec
    for spec in (
        ReasonSpec(
            "postgres_unreachable",
            "db",
            Severity.critical,
            "check the compose db service and its disk",
        ),
        ReasonSpec(
            "redis_unreachable",
            "cache",
            Severity.critical,
            "check the compose redis service",
        ),
        ReasonSpec(
            "worker_heartbeat_stale",
            "worker",
            Severity.critical,
            "restart the worker; check the scheduler log",
        ),
        ReasonSpec(
            "llm_chain_exhausted",
            "summaries",
            Severity.warning,
            "wait for cooldowns; check net:cooldown:*; raise caps if sustained",
        ),
        ReasonSpec(
            "llm_lane_disabled",
            "summaries",
            Severity.critical,
            "rotate the key or clear LLM_DISABLED",
        ),
        ReasonSpec(
            "feed_poller_backlog",
            "news",
            Severity.warning,
            "check provider cooldowns; raise worker concurrency",
        ),
        ReasonSpec(
            "table_provider_cooling", "tables", Severity.info, "none; clears itself"
        ),
        ReasonSpec(
            "briefing_build_stale",
            "briefing",
            Severity.warning,
            "run scripts/briefing.py build",
        ),
        ReasonSpec(
            "scoring_null_rate_high",
            "briefing",
            Severity.warning,
            "check provider health; inspect job_runs",
        ),
        ReasonSpec(
            "engine_unreachable",
            "decisions",
            Severity.warning,
            "start the engine profile or clear ENGINE_URL; chains fall back to the LLM rendering",
        ),
        ReasonSpec(
            "engine_model_missing",
            "decisions",
            Severity.warning,
            "deploy a checkpoint per the runbook",
        ),
        ReasonSpec(
            "scrub_version_lag",
            "publishing",
            Severity.info,
            "none; clears as reads re-scrub",
        ),
    )
}

# `info` and `warning` reasons clear after this long without the condition.
CLEAR_AFTER_SECONDS = 180


@dataclass(frozen=True)
class Reason:
    code: str
    subsystem: str
    severity: Severity
    detail: str
    remedy: str
    since: str  # ISO timestamp of the first observation in the current run


def status_for(reasons: list[Reason]) -> str:
    if any(reason.severity == Severity.critical for reason in reasons):
        return "unhealthy"
    if any(reason.severity == Severity.warning for reason in reasons):
        return "degraded"
    return "ok"
