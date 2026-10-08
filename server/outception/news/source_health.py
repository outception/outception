"""The weekly source health report: which catalog sources have been empty
or failing long enough that disabling them is the honest move. It proposes
rows for `disabled.json`; a person adds them. Nothing is disabled by the
report itself."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from outception.config import settings
from outception.email.sender import (
    DEFAULT_FROM_EMAIL_ADDRESS,
    DEFAULT_FROM_NAME,
    DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    DEFAULT_REPLY_TO_NAME,
)
from outception.net.state import FailureRecord, read_failure
from outception.news.catalog import registry
from outception.redis import Redis
from outception.worker import enqueue_job

# A failure run this old means a week of nothing served; the record itself
# expires after a week of silence, so this is as long as it can be read.
PROPOSE_AFTER_SECONDS = 6 * 24 * 3600


@dataclass(frozen=True)
class Proposal:
    id: str
    name: str
    days: int
    error_class: str

    def as_disabled_row(self, today: datetime) -> dict[str, str]:
        reason = (
            "empty from the production host"
            if self.error_class == "empty"
            else "dead or blocked from the production host"
        )
        return {"id": self.id, "reason": reason, "since": today.date().isoformat()}


def propose(
    failures: dict[str, FailureRecord | None],
    names: dict[str, str],
    now: float | None = None,
    threshold_seconds: float = PROPOSE_AFTER_SECONDS,
) -> list[Proposal]:
    """Sources failing for at least the threshold, longest first. The weekly
    report uses the six-day threshold; an operator can ask for a shorter
    one to see what is failing right now."""
    now = now if now is not None else time.time()
    out: list[Proposal] = []
    for source_id, record in failures.items():
        if record is None:
            continue
        age = now - record.fail_since
        if age < threshold_seconds:
            continue
        out.append(
            Proposal(
                id=source_id,
                name=names.get(source_id, source_id),
                days=int(age // 86400),
                error_class=record.last_error_class,
            )
        )
    out.sort(key=lambda p: (-p.days, p.id))
    return out


async def collect(
    redis: Redis, threshold_seconds: float = PROPOSE_AFTER_SECONDS
) -> list[Proposal]:
    rows = registry().rows
    failures = {sid: await read_failure(redis, sid) for sid in rows}
    return propose(
        failures,
        {sid: row.name for sid, row in rows.items()},
        threshold_seconds=threshold_seconds,
    )


def report_html(proposals: list[Proposal], total: int, today: datetime) -> str:
    lines = [
        f"<p>{len(proposals)} of {total} sources have served nothing for six days or more.</p>"
    ]
    if proposals:
        lines.append("<ul>")
        for p in proposals:
            lines.append(
                f"<li><b>{p.name}</b> ({p.id}): {p.days} days, {p.error_class}</li>"
            )
        lines.append("</ul>")
        lines.append(
            "<p>Rows to add to <code>disabled.json</code> if they stay dark:</p>"
        )
        rows = ",\n".join(
            "  " + str(p.as_disabled_row(today)).replace("'", '"') for p in proposals
        )
        lines.append(f"<pre>[\n{rows}\n]</pre>")
    return "\n".join(lines)


async def send_report(redis: Redis) -> int:
    """Mail the report to the digest address. Returns how many sources it
    proposes; nothing is sent when there is no address or nothing to say."""
    to = settings.FEEDBACK_DIGEST_EMAIL
    proposals = await collect(redis)
    if not to or not proposals:
        return len(proposals)
    today = datetime.now(UTC)
    enqueue_job(
        "email.send",
        to_email_addr=to,
        subject=f"Outception source health: {len(proposals)} source(s) to disable",
        html_content=report_html(proposals, len(registry().rows), today),
        from_name=DEFAULT_FROM_NAME,
        from_email_addr=DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers=None,
        reply_to_name=DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr=DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    )
    return len(proposals)
