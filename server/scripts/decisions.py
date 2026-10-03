"""Shadow-mode reports and training exports for the decision chains.

python -m scripts.decisions report --task score
python -m scripts.decisions export --task score --since 2026-10-01 > scores.jsonl
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from outception.kit.db.postgres import create_async_sessionmaker
from outception.models import NewsCluster, NewsClusterScore
from outception.net.scrub import scrub
from outception.news.briefing.profiles import profiles
from outception.news.briefing.questions import score_questions
from outception.news.clusters.decisions import shadow_report
from outception.postgres import create_async_engine
from outception.redis import create_redis

TASKS = ("score", "category", "route", "resolve")


async def report(task: str) -> int:
    redis = create_redis("script")
    try:
        result = await shadow_report(redis, task)
    finally:
        await redis.close()
    print(json.dumps(result, indent=2))
    return 0


async def export(task: str, since: str) -> int:
    """JSONL of {state, questions, answer}: the house engine's training
    record shape. Scrubbed; no reader data, no keys."""
    if task != "score":
        print("only the score task exports today", file=sys.stderr)
        return 1
    start = datetime.fromisoformat(since).replace(tzinfo=UTC)
    engine = create_async_engine("script")
    sessionmaker = create_async_sessionmaker(engine)
    count = 0
    try:
        async with sessionmaker() as session:
            result = await session.execute(
                select(NewsCluster, NewsClusterScore)
                .join(NewsClusterScore, NewsClusterScore.cluster_id == NewsCluster.id)
                .where(
                    NewsClusterScore.scored_at >= start,
                    NewsClusterScore.score.is_not(None),
                )
            )
            for cluster, score in result.all():
                profile = profiles().get(score.profile_id)
                if profile is None:
                    continue
                questions = [
                    {
                        "id": q.id,
                        "kind": q.kind,
                        "text": q.text,
                        "options": list(q.options),
                    }
                    for q in score_questions(profile)
                ]
                record = {
                    "task": "score",
                    "profile": profile.id,
                    "state": {
                        "title": scrub(cluster.title),
                        "publisher_count": score.publisher_count,
                    },
                    "questions": questions,
                    "answer": {"score": str(score.score), "category": score.category},
                    "label_source": "llm",
                    "scored_at": score.scored_at.isoformat(),
                }
                print(json.dumps(record, ensure_ascii=False))
                count += 1
    finally:
        await engine.dispose()
    print(f"{count} records", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="decisions")
    commands = parser.add_subparsers(dest="command", required=True)
    report_parser = commands.add_parser("report")
    report_parser.add_argument("--task", choices=TASKS, required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--task", choices=TASKS, required=True)
    export_parser.add_argument("--since", required=True)
    args = parser.parse_args(argv)
    if args.command == "report":
        return asyncio.run(report(args.task))
    return asyncio.run(export(args.task, args.since))


if __name__ == "__main__":
    sys.exit(main())
