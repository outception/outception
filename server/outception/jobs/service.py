import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update

from outception.kit.utils import utc_now
from outception.models import JobKind, JobRun, JobState
from outception.net.scrub import scrub
from outception.postgres import AsyncSession

ERROR_DETAIL_CHARS = 500
INTERRUPTED = "interrupted"


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def _detail(error: BaseException | str | None) -> str | None:
    if error is None:
        return None
    return scrub(str(error))[:ERROR_DETAIL_CHARS] or None


async def start_run(
    session: AsyncSession,
    kind: JobKind,
    subject: str,
    *,
    lane: str,
    prompt_version: str | None = None,
    prompt_digest: str | None = None,
    retry_of: UUID | None = None,
) -> JobRun:
    run = JobRun(
        kind=kind,
        subject=subject[:256],
        state=JobState.running,
        lane=lane,
        prompt_version=prompt_version,
        prompt_digest=prompt_digest,
        retry_of=retry_of,
        started_at=utc_now(),
    )
    session.add(run)
    await session.flush()
    return run


async def finish_run(
    session: AsyncSession,
    run: JobRun,
    *,
    served_model: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> None:
    run.state = JobState.completed
    run.served_model = served_model
    run.tokens_in = tokens_in
    run.tokens_out = tokens_out
    run.finished_at = utc_now()
    await session.flush()


async def fail_run(
    session: AsyncSession,
    run: JobRun,
    *,
    error_class: str,
    error: BaseException | str | None = None,
    state: JobState = JobState.failed,
) -> None:
    run.state = state
    run.error_class = error_class[:32]
    run.error_detail = _detail(error)
    run.finished_at = utc_now()
    await session.flush()


@dataclass
class JobContext:
    run: JobRun
    served_model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None

    def served(self, model: str, *, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.served_model = model
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out


@asynccontextmanager
async def record_run(
    session: AsyncSession,
    kind: JobKind,
    subject: str,
    *,
    lane: str,
    prompt_version: str | None = None,
    prompt: str | None = None,
    retry_of: UUID | None = None,
) -> AsyncIterator[JobContext]:
    """Record one call. The body reports what answered through
    `context.served(...)`; an exception closes the row as failed with the
    error's class (a `ModelError` carries one; anything else is internal)
    and re-raises."""
    run = await start_run(
        session,
        kind,
        subject,
        lane=lane,
        prompt_version=prompt_version,
        prompt_digest=prompt_digest(prompt) if prompt else None,
        retry_of=retry_of,
    )
    context = JobContext(run)
    try:
        yield context
    except BaseException as error:
        error_class = str(getattr(error, "error_class", None) or "internal")
        await fail_run(session, run, error_class=error_class, error=error)
        raise
    await finish_run(
        session,
        run,
        served_model=context.served_model,
        tokens_in=context.tokens_in,
        tokens_out=context.tokens_out,
    )


async def mark_interrupted(session: AsyncSession) -> int:
    """At worker boot: a run still `running` was interrupted by the
    previous process; close it so it never reads as in flight forever."""
    result = await session.execute(
        update(JobRun)
        .where(JobRun.state.in_((JobState.queued, JobState.running)))
        .values(
            state=JobState.timed_out,
            error_detail=INTERRUPTED,
            finished_at=utc_now(),
        )
    )
    await session.flush()
    return int(getattr(result, "rowcount", 0) or 0)


async def recent_runs(
    session: AsyncSession, *, kind: JobKind | None = None, limit: int = 50
) -> list[JobRun]:
    statement = select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)
    if kind is not None:
        statement = statement.where(JobRun.kind == kind)
    return list((await session.execute(statement)).scalars().all())
