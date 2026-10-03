"""YouTube - latest uploads per channel from the channel page's own data.

YouTube's per-channel Atom feed (``/feeds/videos.xml?channel_id=<id>``)
served every source here until 2026-09, when the endpoint started
answering 404 for every channel - including the URL each channel page
still advertises in its own markup. The uploads are read from the
``/videos`` tab instead: the page embeds ``ytInitialData`` with the same
~30 most recent uploads the feed used to carry. Upload times only reach
the page as relative text ("3 hours ago"), so ``pub_date`` is
approximate - fine for card ordering, which is all it feeds.
"""

import asyncio
import json
import re
import time
from typing import Any

from ..catalog import registry as catalog_registry
from ..fetch import NewsFetchError, fetch_text
from ..registry import register
from ..schemas import NewsItem

# "Streamed 3 hours ago" / "2 weeks ago" → seconds before now.
_AGO_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
    "year": 31536000,
}
_AGO_RE = re.compile(r"(\d+)\s+(second|minute|hour|day|week|month|year)")


def _published_ms(text: str | None, now_ms: int) -> int | None:
    if not text:
        return None
    match = _AGO_RE.search(text)
    if match is None:
        return None
    return now_ms - int(match.group(1)) * _AGO_SECONDS[match.group(2)] * 1000


def _initial_data(page: str) -> dict[str, Any]:
    marker = "var ytInitialData = "
    start = page.find(marker)
    if start < 0:
        raise NewsFetchError("no ytInitialData on channel page")
    start += len(marker)
    end = page.find(";</script>", start)
    if end < 0:
        raise NewsFetchError("unterminated ytInitialData on channel page")
    return json.loads(page[start:end])


def _uploads(data: dict[str, Any], now_ms: int) -> list[NewsItem]:
    try:
        tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
    except (KeyError, TypeError) as exc:
        # Consent/captcha interstitials carry ytInitialData with none of the
        # channel structure - a fetch failure, not a crash.
        raise NewsFetchError("channel page has no tab structure") from exc
    grid = None
    for tab in tabs:
        content = tab.get("tabRenderer", {}).get("content", {})
        if "richGridRenderer" in content:
            grid = content["richGridRenderer"]
            break
    if grid is None:
        raise NewsFetchError("no uploads grid on channel page")
    items: list[NewsItem] = []
    for cell in grid.get("contents", []):
        content = cell.get("richItemRenderer", {}).get("content", {})
        video_id: str | None = None
        title: str | None = None
        published: str | None = None
        # YouTube is mid-migration between two grid components; channels
        # serve either, so both are read.
        if "lockupViewModel" in content:
            lockup = content["lockupViewModel"]
            video_id = lockup.get("contentId")
            meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
            title = meta.get("title", {}).get("content")
            rows = (
                meta.get("metadata", {})
                .get("contentMetadataViewModel", {})
                .get("metadataRows", [])
            )
            for row in rows:
                for part in row.get("metadataParts", []):
                    text = part.get("text", {}).get("content", "")
                    if _AGO_RE.search(text):
                        published = text
                        break
                if published is not None:
                    break
        elif "videoRenderer" in content:
            video = content["videoRenderer"]
            video_id = video.get("videoId")
            runs = video.get("title", {}).get("runs", [])
            title = runs[0]["text"] if runs else None
            published = video.get("publishedTimeText", {}).get("simpleText")
        if not video_id or not title:
            continue
        url = f"https://www.youtube.com/watch?v={video_id}"
        items.append(
            NewsItem(
                id=url,
                title=title,
                url=url,
                pub_date=_published_ms(published, now_ms),
            )
        )
    return items


def _make_getter(channel_id: str, source_id: str) -> None:
    _url = f"https://www.youtube.com/channel/{channel_id}/videos"

    async def _getter() -> list[NewsItem]:
        # SOCS skips the EU consent interstitial (same cookie gnews uses);
        # the client's Accept-Language keeps publishedTimeText in English so
        # the relative-time parse holds.
        page = await fetch_text(_url, headers={"Cookie": "SOCS=CAI"})
        # The embedded JSON runs to ~1 MB - parse it off the event loop.
        data = await asyncio.to_thread(_initial_data, page)
        items = _uploads(data, int(time.time() * 1000))
        if not items:
            raise NewsFetchError(f"Cannot fetch YouTube uploads for {source_id}")
        return items[:30]

    register(source_id, _getter)


for _row in catalog_registry().rows.values():
    if _row.adapter == "youtube":
        _make_getter(str(_row.config["channel_id"]), _row.id)
