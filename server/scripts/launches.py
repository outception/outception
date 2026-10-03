"""The review page for the terminal.

python -m scripts.launches list [--state submitted]
python -m scripts.launches approve <id> <day> [--featured]
python -m scripts.launches reject <id> [--note "..."]
python -m scripts.launches feature <id>
python -m scripts.launches end <id>
"""

import argparse
import asyncio
import sys
from datetime import date
from uuid import UUID

from sqlalchemy import select

from outception.kit.db.postgres import create_async_sessionmaker
from outception.launches import service
from outception.launches.schemas import LaunchApprove
from outception.models import Launch, LaunchStatus
from outception.postgres import create_async_engine
from outception.redis import create_redis


def _line(launch: Launch) -> str:
    return (
        f"{launch.id}  {launch.state:<10} {launch.day or '-':<10} "
        f"{launch.position or '-':<2} {'*' if launch.featured else ' '} "
        f"{launch.name}: {launch.tagline}  {launch.url}"
    )


async def run(args: argparse.Namespace) -> int:
    engine = create_async_engine("script")
    sessionmaker = create_async_sessionmaker(engine)
    redis = create_redis("script")
    code = 0
    try:
        async with sessionmaker() as session:
            if args.command == "list":
                statement = select(Launch).order_by(Launch.created_at.desc())
                if args.state:
                    statement = statement.where(
                        Launch.state == LaunchStatus(args.state)
                    )
                for launch in (await session.execute(statement)).scalars().all():
                    print(_line(launch))
            elif args.command == "approve":
                launch = await service.approve(
                    session,
                    redis,
                    UUID(args.id),
                    LaunchApprove(
                        day=date.fromisoformat(args.day), featured=args.featured
                    ),
                )
                print(_line(launch))
            elif args.command == "reject":
                print(
                    _line(await service.reject(session, UUID(args.id), args.note or ""))
                )
            elif args.command == "feature":
                launch = await service.get(session, UUID(args.id))
                launch.featured = True
                await session.flush()
                await service.rebuild_card(session, redis)
                print(_line(launch))
            elif args.command == "end":
                launch = await service.get(session, UUID(args.id))
                launch.state = LaunchStatus.ended
                await session.flush()
                await service.rebuild_card(session, redis)
                print(_line(launch))
            await session.commit()
    finally:
        await redis.close()
        await engine.dispose()
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="launches")
    commands = parser.add_subparsers(dest="command", required=True)
    list_parser = commands.add_parser("list")
    list_parser.add_argument("--state", choices=[s.value for s in LaunchStatus])
    approve_parser = commands.add_parser("approve")
    approve_parser.add_argument("id")
    approve_parser.add_argument("day")
    approve_parser.add_argument("--featured", action="store_true")
    reject_parser = commands.add_parser("reject")
    reject_parser.add_argument("id")
    reject_parser.add_argument("--note")
    for name in ("feature", "end"):
        commands.add_parser(name).add_argument("id")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
