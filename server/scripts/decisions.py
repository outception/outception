"""Shadow-mode reports for the decision chains.

python -m scripts.decisions report --task resolve
"""

import argparse
import asyncio
import json
import sys

from outception.news.clusters.decisions import shadow_report
from outception.redis import create_redis

TASKS = ("resolve",)


async def report(task: str) -> int:
    redis = create_redis("script")
    try:
        result = await shadow_report(redis, task)
    finally:
        await redis.close()
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="decisions")
    commands = parser.add_subparsers(dest="command", required=True)
    report_parser = commands.add_parser("report")
    report_parser.add_argument("--task", choices=TASKS, required=True)
    args = parser.parse_args(argv)
    return asyncio.run(report(args.task))


if __name__ == "__main__":
    sys.exit(main())
