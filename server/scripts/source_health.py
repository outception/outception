"""Print the source health report: sources failing for six days or more,
with the rows a person would add to `disabled.json`.

python -m scripts.source_health [--json]
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from outception.news import source_health
from outception.redis import create_redis


async def run(as_json: bool, days: float) -> int:
    redis = create_redis("script")
    try:
        proposals = await source_health.collect(redis, days * 24 * 3600)
    finally:
        await redis.close()
    today = datetime.now(UTC)
    if as_json:
        print(json.dumps([p.as_disabled_row(today) for p in proposals], indent=2))
        return 0
    if not proposals:
        print(f"every source has served something in the last {days:g} days")
        return 0
    for p in proposals:
        print(f"{p.id:<32} {p.days:>3} days  {p.error_class:<10} {p.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="source_health")
    parser.add_argument("--json", action="store_true", help="print disabled.json rows")
    parser.add_argument(
        "--days", type=float, default=6, help="how long a run must be to count"
    )
    args = parser.parse_args(argv)
    return asyncio.run(run(args.json, args.days))


if __name__ == "__main__":
    sys.exit(main())
