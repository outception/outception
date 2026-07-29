"""Daily puzzle feeds for the wall's mini-game cards.

The crossword is the syndicated daily puzzle: a plain-text format of solution
grid + clue lists, fetched once a day and cached in Redis — readers get the
parsed JSON from cache, never the upstream. The text format is line-based:
line 2 = puzzle id, 4 = title, 6 = author, 8 = rows, 10 = cols, 12/14 = clue
counts, then the solution grid rows (``#`` = block, ``%`` marks stripped),
then the across clues, then the down clues.
"""

import asyncio
import json
from typing import Any

import structlog

from outception.exceptions import OutceptionError
from outception.redis import Redis

from .fetch import NewsFetchError, fetch_text

log = structlog.get_logger()

_XWORD_URL = "https://nytsyn.pzzl.com/nytsyn-crossword-mh/nytsyncrossword"
_XWORD_CACHE_KEY = "news:games:crossword:{date}"
_XWORD_TTL_SECONDS = 26 * 60 * 60  # a day plus slack for timezone edges
# After an upstream failure, hold off retrying for a couple of minutes: a dead
# syndicate feed must not turn every reader request into an upstream hit
# (both a hammering and a latency problem — fail fast from the marker instead).
_XWORD_FAIL_KEY = "news:games:crossword:fail:{date}"
_XWORD_FAIL_TTL_SECONDS = 120
# Single-flight election for the daily fetch (same pattern as the heatmaps):
# the cache is empty for everyone at once right after the UTC rollover, so
# without a winner every concurrent reader would hit the syndicate together.
# Non-winners re-poll the cache briefly for the winner's write, then fall back.
_XWORD_REFETCH_KEY = "news:games:crossword:refetch:{date}"
# The winner's own ceiling. httpx times out per OPERATION and the transport
# retries, so without this the fetch has no whole-call bound — and every
# waiter below is holding a request against it.
_XWORD_FETCH_SECONDS = 8.0
# The election lock outlives one bounded attempt and no more: a winner killed
# mid-fetch (deploy, OOM) publishes no failure marker, so the lock expiring is
# what tells the waiters to stop — and what lets the next reader retry. It is
# NOT the upstream throttle; the failure marker is.
_XWORD_REFETCH_TTL_SECONDS = 10
# A cold upstream fetch of the syndicate feed routinely takes several
# seconds, and 2s of waiting handed every concurrent reader YESTERDAY's grid
# as a successful response — a correctness regression traded for the
# stampede fix. So wait past a realistic fetch — but never past the winner's
# own ceiling, since nothing can arrive after it. Derived from the lock rather
# than written as a count, so the two can't drift apart.
_XWORD_POLL_SECONDS = 0.25
_XWORD_POLL_ATTEMPTS = int(_XWORD_REFETCH_TTL_SECONDS / _XWORD_POLL_SECONDS)


def parse_crossword(text: str) -> dict[str, Any]:
    """Parse the syndicate text format into the JSON the game renders.

    Numbering follows the standard rule: a cell starts a clue when it is
    enterable and the cell before it (in that direction) is a block or the
    edge; a single counter numbers cells in reading order.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    rows = int(lines[8])
    cols = int(lines[10])
    across_count = int(lines[12])
    down_count = int(lines[14])
    grid = [lines[16 + i].replace("%", "") for i in range(rows)]
    across_text = [lines[17 + rows + i] for i in range(across_count)]
    down_text = [lines[18 + rows + across_count + i] for i in range(down_count)]

    # Larger deliveries pad the grid with '.' void filler (a whole row or
    # column of dots): trim fully-void edges, then treat any stray void cell
    # as a block so numbering and rendering stay consistent.
    while grid and set(grid[-1]) <= {"."}:
        grid.pop()
    while grid and set(grid[0]) <= {"."}:
        grid.pop(0)
    while grid and all(g and g[-1] == "." for g in grid):
        grid = [g[:-1] for g in grid]
    while grid and all(g and g[0] == "." for g in grid):
        grid = [g[1:] for g in grid]
    grid = [g.replace(".", "#") for g in grid]
    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    across: list[dict[str, Any]] = []
    down: list[dict[str, Any]] = []
    number = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "#":
                continue
            # A run must be at least two cells to count as a word — a lone
            # cell walled in on one axis is only part of the crossing word
            # and never gets a clue of its own (larger grids hit this).
            across_len = 0
            while c + across_len < cols and grid[r][c + across_len] != "#":
                across_len += 1
            down_len = 0
            while r + down_len < rows and grid[r + down_len][c] != "#":
                down_len += 1
            starts_across = (c == 0 or grid[r][c - 1] == "#") and across_len >= 2
            starts_down = (r == 0 or grid[r - 1][c] == "#") and down_len >= 2
            if not (starts_across or starts_down):
                continue
            number += 1
            if starts_across:
                across.append(
                    {
                        "num": number,
                        "clue": across_text[len(across)],
                        "row": r,
                        "col": c,
                        "len": across_len,
                    }
                )
            if starts_down:
                down.append(
                    {
                        "num": number,
                        "clue": down_text[len(down)],
                        "row": r,
                        "col": c,
                        "len": down_len,
                    }
                )
    return {
        "id": lines[2],
        "title": lines[4],
        "author": lines[6],
        "rows": rows,
        "cols": cols,
        "grid": grid,
        "across": across,
        "down": down,
    }


async def _cached_puzzle(redis: Redis, date_str: str) -> dict[str, Any] | None:
    cached = await redis.get(_XWORD_CACHE_KEY.format(date=date_str))
    if cached is None:
        return None
    try:
        return json.loads(cached)
    except ValueError:
        return None


async def get_crossword(
    redis: Redis, date_str: str, fallback_date_str: str | None = None
) -> dict[str, Any]:
    """Today's parsed crossword, cache-first (one upstream fetch per day).

    ``date_str`` is YYMMDD, computed by the caller from UTC so every reader
    worldwide solves the same puzzle on the same key. Around the UTC midnight
    rollover the syndicate may not have published the new puzzle yet — rather
    than an empty card, ``fallback_date_str`` (yesterday) keeps serving the
    previous puzzle from cache until today's appears.
    """
    puzzle = await _cached_puzzle(redis, date_str)
    if puzzle is not None:
        return puzzle
    fail_key = _XWORD_FAIL_KEY.format(date=date_str)
    upstream_blocked = await redis.get(fail_key) is not None
    if not upstream_blocked:
        won = await redis.set(
            _XWORD_REFETCH_KEY.format(date=date_str),
            "1",
            ex=_XWORD_REFETCH_TTL_SECONDS,
            nx=True,
        )
        if won:
            try:
                text = await asyncio.wait_for(
                    fetch_text(_XWORD_URL, params={"date": date_str}),
                    _XWORD_FETCH_SECONDS,
                )
                # The parse is pure CPU over a whole grid — keep it off the
                # event loop like the RSS/HTML parses in fetch.py.
                puzzle = await asyncio.to_thread(parse_crossword, text)
            # TimeoutError included: a winner that ran out of time must publish
            # the marker like any other failure, or its waiters poll on for a
            # write that can no longer come.
            except (NewsFetchError, TimeoutError, ValueError, IndexError) as exc:
                log.info("news.crossword_failed", date=date_str, error=str(exc))
                await redis.set(fail_key, "1", ex=_XWORD_FAIL_TTL_SECONDS)
            else:
                await redis.set(
                    _XWORD_CACHE_KEY.format(date=date_str),
                    json.dumps(puzzle),
                    ex=_XWORD_TTL_SECONDS,
                )
                return puzzle
        else:
            # Another request is fetching: wait briefly for its cache write
            # instead of piling onto the upstream, then serve the fallback.
            refetch_key = _XWORD_REFETCH_KEY.format(date=date_str)
            for _ in range(_XWORD_POLL_ATTEMPTS):
                await asyncio.sleep(_XWORD_POLL_SECONDS)
                puzzle = await _cached_puzzle(redis, date_str)
                if puzzle is not None:
                    return puzzle
                if await redis.get(fail_key) is not None:
                    break  # the winner failed; stop waiting for a write
                if await redis.get(refetch_key) is None:
                    # The winner's lock expired without either outcome: it was
                    # killed mid-fetch. Nothing is coming — don't ride out the
                    # rest of the ladder waiting on a process that is gone.
                    break
    if fallback_date_str is not None:
        fallback = await _cached_puzzle(redis, fallback_date_str)
        if fallback is not None:
            return fallback
    raise OutceptionError("Crossword is unavailable", status_code=502)
