"""Operator view of the job runs.

python -m scripts.jobs tail [--kind score] [--limit 50]
python -m scripts.jobs show <id>
"""

import argparse
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from outception.jobs.service import recent_runs
from outception.kit.db.postgres import create_async_sessionmaker
from outception.models import JobKind, JobRun
from outception.postgres import create_async_engine


def _line(run: JobRun) -> str:
    finished = run.finished_at.isoformat(timespec="seconds") if run.finished_at else "-"
    return (
        f"{run.id}  {run.kind:<10} {run.state:<10} {run.lane:<12} "
        f"{run.served_model or '-':<24} {run.started_at.isoformat(timespec='seconds')}  "
        f"{finished}  {run.error_class or ''} {run.error_detail or ''}"
    ).rstrip()


async def tail(kind: str | None, limit: int) -> int:
    engine = create_async_engine("script")
    sessionmaker = create_async_sessionmaker(engine)
    async with sessionmaker() as session:
        runs = await recent_runs(
            session, kind=JobKind(kind) if kind else None, limit=limit
        )
    await engine.dispose()
    for run in runs:
        print(_line(run))
    return 0


async def show(run_id: str) -> int:
    engine = create_async_engine("script")
    sessionmaker = create_async_sessionmaker(engine)
    async with sessionmaker() as session:
        run = await session.scalar(select(JobRun).where(JobRun.id == UUID(run_id)))
    await engine.dispose()
    if run is None:
        print("no such run", file=sys.stderr)
        return 1
    for name in (
        "id",
        "kind",
        "subject",
        "state",
        "lane",
        "served_model",
        "prompt_version",
        "prompt_digest",
        "tokens_in",
        "tokens_out",
        "error_class",
        "error_detail",
        "retry_of",
        "started_at",
        "finished_at",
    ):
        print(f"{name:<16} {getattr(run, name)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    tail_parser = commands.add_parser("tail")
    tail_parser.add_argument("--kind", choices=[kind.value for kind in JobKind])
    tail_parser.add_argument("--limit", type=int, default=50)
    show_parser = commands.add_parser("show")
    show_parser.add_argument("id")
    args = parser.parse_args(argv)
    if args.command == "tail":
        return asyncio.run(tail(args.kind, args.limit))
    return asyncio.run(show(args.id))


if __name__ == "__main__":
    sys.exit(main())
