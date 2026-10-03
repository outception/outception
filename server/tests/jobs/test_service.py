from datetime import timedelta

import pytest
from sqlalchemy import select

from outception.jobs import mark_interrupted, record_run
from outception.jobs.service import recent_runs
from outception.kit.utils import utc_now
from outception.models import JobKind, JobRun, JobState
from outception.news.summaries.providers.classes import ErrorClass, ModelError
from outception.postgres import AsyncSession


@pytest.mark.asyncio
class TestRecordRun:
    async def test_completed_run_keeps_what_answered(
        self, session: AsyncSession
    ) -> None:
        async with record_run(
            session,
            JobKind.summary,
            "digest-1",
            lane="interactive",
            prompt_version="1",
            prompt="the rendered prompt",
        ) as context:
            context.served("first-line-model", tokens_in=120, tokens_out=40)
        await session.commit()
        run = await session.scalar(select(JobRun))
        assert run is not None
        assert run.state == JobState.completed
        assert run.served_model == "first-line-model"
        assert (run.tokens_in, run.tokens_out) == (120, 40)
        assert run.prompt_version == "1"
        assert run.prompt_digest is not None
        assert len(run.prompt_digest) == 64
        assert run.finished_at is not None

    async def test_failed_run_carries_the_class_and_a_scrubbed_detail(
        self, session: AsyncSession
    ) -> None:
        with pytest.raises(ModelError):
            async with record_run(
                session, JobKind.score, "cluster-1", lane="background"
            ):
                raise ModelError(
                    "first-line",
                    ErrorClass.quota,
                    detail="key sk-abcdefghijklmnopqrstuvwxyz1234",
                )
        await session.commit()
        run = await session.scalar(select(JobRun))
        assert run is not None
        assert run.state == JobState.failed
        assert run.error_class == "quota"
        assert run.error_detail is not None
        assert "[secret]" in run.error_detail
        assert "sk-abcdef" not in run.error_detail

    async def test_unknown_errors_are_internal(self, session: AsyncSession) -> None:
        with pytest.raises(RuntimeError):
            async with record_run(
                session, JobKind.build, "developer", lane="background"
            ):
                raise RuntimeError("boom")
        run = await session.scalar(select(JobRun))
        assert run is not None
        assert run.error_class == "internal"

    async def test_boot_sweep_closes_open_runs(self, session: AsyncSession) -> None:
        open_run = JobRun(
            kind=JobKind.resolve,
            subject="pair",
            state=JobState.running,
            lane="background",
            started_at=utc_now() - timedelta(minutes=5),
        )
        done = JobRun(
            kind=JobKind.resolve,
            subject="pair",
            state=JobState.completed,
            lane="background",
            started_at=utc_now() - timedelta(minutes=5),
            finished_at=utc_now(),
        )
        session.add_all([open_run, done])
        await session.flush()
        assert await mark_interrupted(session) == 1
        await session.refresh(open_run)
        assert open_run.state == JobState.timed_out
        assert open_run.error_detail == "interrupted"
        await session.refresh(done)
        assert done.state == JobState.completed

    async def test_recent_runs_filter_by_kind(self, session: AsyncSession) -> None:
        for kind in (JobKind.summary, JobKind.score, JobKind.summary):
            async with record_run(session, kind, "x", lane="background"):
                pass
        assert len(await recent_runs(session)) == 3
        assert len(await recent_runs(session, kind=JobKind.summary)) == 2
