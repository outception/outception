"""Bluesky — What's Hot feed via the public AppView API."""

from ..fetch import fetch_json
from ..registry import source
from ..schemas import NewsExtra, NewsItem

_URL = (
    "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"
    "?feed=at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot"
    "&limit=30"
)
_MAX_TITLE = 140


@source("bluesky")
async def bluesky() -> list[NewsItem]:
    data = await fetch_json(_URL)
    items: list[NewsItem] = []
    for item in data.get("feed", []):
        post = item["post"]
        text = post["record"].get("text", "")
        if not text:
            continue
        if len(text) > _MAX_TITLE:
            text = text[:_MAX_TITLE] + "…"
        rkey = post["uri"].rsplit("/", 1)[-1]
        handle = post["author"]["handle"]
        url = f"https://bsky.app/profile/{handle}/post/{rkey}"
        items.append(
            NewsItem(
                id=post["uri"],
                title=text,
                url=url,
                extra=NewsExtra(info=f"{post.get('likeCount', 0)} likes"),
            )
        )
    return items
