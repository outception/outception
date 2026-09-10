"""Operator controls for the Promoted card. No self-serve flow exists on
purpose: slots are provisioned here when a Push package is sold on
outception.ai, and every ad is approved by the founder before it runs.

Usage (from server/):

    uv run python -m scripts.promoted status
    uv run python -m scripts.promoted queue \
        --business "Corner Cafe" \
        --video https://cdn.example.com/ads/corner-cafe.mp4 \
        --click https://cornercafe.example \
        --tagline "Fresh pastries daily" \
        --hours 168
    uv run python -m scripts.promoted stop     # end the active run now
    uv run python -m scripts.promoted clear    # drop the whole queue
"""

import argparse
import asyncio
import secrets

from outception.promoted import service
from outception.promoted.schemas import QueuedPromotion
from outception.redis import create_redis


async def _status() -> None:
    redis = create_redis("script")
    active = await service.get_active(redis)
    if active is None:
        print("active: none")
    else:
        print(
            f"active: {active.id} {active.business_name!r} until {active.ends_at:%Y-%m-%d %H:%M} UTC"
        )
    queue = await service.list_queue(redis)
    print(f"queued: {len(queue)}")
    for i, q in enumerate(queue, 1):
        hours = q.duration_seconds / 3600
        print(f"  {i}. {q.id} {q.business_name!r} ({hours:g}h)")
    dead = await redis.llen(service.DEAD_KEY)
    if dead:
        print(f"dead-lettered (malformed, never served): {dead}")
    await redis.close()


async def _queue(args: argparse.Namespace) -> None:
    redis = create_redis("script")
    promotion = QueuedPromotion(
        id=secrets.token_urlsafe(8),
        business_name=args.business,
        video_url=args.video,
        click_url=args.click,
        tagline=args.tagline,
        duration_seconds=int(args.hours * 3600),
    )
    length = await service.enqueue(redis, promotion)
    print(f"queued {promotion.id} at position {length}")
    await redis.close()


async def _stop() -> None:
    redis = create_redis("script")
    stopped = await service.stop_active(redis)
    print("stopped active run" if stopped else "no active run")
    await redis.close()


async def _clear() -> None:
    redis = create_redis("script")
    await service.clear_queue(redis)
    print("queue cleared")
    await redis.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    queue = sub.add_parser("queue")
    queue.add_argument("--business", required=True)
    queue.add_argument("--video", required=True)
    queue.add_argument("--click", default=None)
    queue.add_argument("--tagline", default=None)
    queue.add_argument("--hours", type=float, default=168.0)
    sub.add_parser("stop")
    sub.add_parser("clear")
    args = parser.parse_args()
    if args.command == "status":
        asyncio.run(_status())
    elif args.command == "queue":
        asyncio.run(_queue(args))
    elif args.command == "stop":
        asyncio.run(_stop())
    elif args.command == "clear":
        asyncio.run(_clear())


if __name__ == "__main__":
    main()
