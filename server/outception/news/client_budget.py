"""Per-caller allowances for work that is cheap to ASK for and expensive to DO.

Some routes take a caller-supplied value with millions of distinct possibilities
and turn each new one into real work against a small shared budget: an uncached
weather cell is one call against a global daily cap on the upstream, and
``?latest=`` on a cold source is one of 24 outbound fetch slots. Per-value
guards (a cache entry, a per-source cooldown) never repeat for a caller that
simply keeps picking new values, and the route's own rate limit counts requests
rather than the shared resource behind them. One client could therefore spend
the whole day's upstream budget, or hold every fetch slot, and the failure then
lands on everyone.

These allowances bound how much of a shared resource any single client may
consume. They sit UNDER the route rate limits: a normal reader looks at one or
two weather locations and a handful of cards, so the ceilings here are far above
real use and only bite on a pattern no reader produces.
"""

from outception.redis import Redis

_KEY = "news:clientbudget:{bucket}:{client}:{window}"


async def spend(
    redis: Redis,
    bucket: str,
    client: str | None,
    *,
    limit: int,
    window_seconds: int,
) -> bool:
    """Charge one unit of *bucket* to *client*; False when they are over.

    Fails OPEN when the caller cannot be identified (no client address): a
    missing header must degrade to today's behaviour, never to a blanket
    refusal that would take out readers behind a proxy we failed to parse.
    """
    if not client:
        return True
    key = _KEY.format(bucket=bucket, client=client, window=window_seconds)
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, window_seconds)
    return used <= limit
