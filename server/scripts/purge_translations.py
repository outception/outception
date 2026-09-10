"""Drop the Redis state the removed translation pipeline left behind.

Headlines are served in English only now, so nothing reads `news:xlate:*` any
more: the headline cache, the per-language demand counters, the paid/free daily
budgets, the pending and failed markers, the per-provider latency samples and
the per-source language demand. They carry TTLs and would expire on their own,
but the cache entries hold the bulk of the keyspace and there is no reason to
pay for them until then.

Also drains the non-English entries from the summary warm queue. Those are
skipped by the warmer now (it takes English only), so left alone they sit in
the set and are re-examined on every run.

Usage (from server/):

    uv run python -m scripts.purge_translations --dry-run
    uv run python -m scripts.purge_translations
"""

import argparse
import asyncio

from outception.redis import create_redis

# Every key the translation pipeline wrote shared this prefix.
_TRANSLATION_PREFIX = "news:xlate:*"
# Members are "<lang>\t<url>"; anything not English is now unreachable work.
_WARM_QUEUE = "news:summary:warm:pretap"
# SCAN in batches rather than KEYS: this runs against production Redis, where
# KEYS on a multi-million-key space blocks the server for everyone.
_SCAN_COUNT = 500


async def purge(dry_run: bool) -> None:
    redis = create_redis("app")
    try:
        scanned = 0
        deleted = 0
        async for key in redis.scan_iter(match=_TRANSLATION_PREFIX, count=_SCAN_COUNT):
            scanned += 1
            if not dry_run:
                await redis.delete(key)
                deleted += 1
        print(f"news:xlate:* matched {scanned}, deleted {deleted}")

        members = await redis.smembers(_WARM_QUEUE)
        stale = [
            member
            for member in members
            if not (
                member.decode() if isinstance(member, bytes) else member
            ).startswith("en\t")
        ]
        if stale and not dry_run:
            await redis.srem(_WARM_QUEUE, *stale)
        print(f"{_WARM_QUEUE}: {len(members)} members, {len(stale)} non-English")
    finally:
        # `aclose` is the non-deprecated name from redis-py 5.0.1; the bundled
        # type stubs still only describe `close`, so the call is correct at
        # runtime and invisible to the checker.
        await redis.aclose()  # type: ignore[attr-defined]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what would go without deleting anything.",
    )
    args = parser.parse_args()
    asyncio.run(purge(args.dry_run))
