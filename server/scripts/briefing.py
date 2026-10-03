"""Build or show a briefing from the terminal.

python -m scripts.briefing build <profile>
python -m scripts.briefing show <profile>
python -m scripts.briefing profiles
"""

import argparse
import asyncio
import json
import sys

from outception.kit.db.postgres import create_async_sessionmaker
from outception.news.briefing import builder, service
from outception.news.briefing.profiles import profiles
from outception.postgres import create_async_engine
from outception.redis import create_redis


async def run(args: argparse.Namespace) -> int:
    if args.command == "profiles":
        for profile in profiles().values():
            print(
                f"{profile.id:<14} {profile.template:<14} {', '.join(profile.category_ids)}"
            )
        return 0
    found = service.get_profile(args.profile)
    if found is None:
        print(f"unknown profile {args.profile}", file=sys.stderr)
        return 1
    profile = found
    redis = create_redis("script")
    try:
        if args.command == "show":
            briefing = await service.latest(redis, profile)
            if briefing is None:
                print("no briefing built yet")
                return 1
            print(json.dumps(briefing.model_dump(by_alias=True, mode="json"), indent=2))
            return 0
        engine = create_async_engine("script")
        sessionmaker = create_async_sessionmaker(engine)
        try:
            async with sessionmaker() as session:
                built = await builder.build(session, redis, profile)
                await session.commit()
        finally:
            await engine.dispose()
        if built is None:
            print("another build holds the lock")
            return 1
        print(f"built {len(built.items)} items for {profile.id}")
        return 0
    finally:
        await redis.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="briefing")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("profiles")
    for name in ("build", "show"):
        commands.add_parser(name).add_argument("profile")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
