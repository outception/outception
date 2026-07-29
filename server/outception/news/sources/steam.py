"""Steam — current player counts ranking."""

import time

from ..fetch import fetch_html
from ..registry import source
from ..schemas import NewsExtra, NewsItem


@source("steam")
async def steam() -> list[NewsItem]:
    soup = await fetch_html("https://store.steampowered.com/stats/stats/")
    now = int(time.time() * 1000)
    items: list[NewsItem] = []
    for el in soup.select("#detailStats tr.player_count_row"):
        a = el.select_one("a.gameLink")
        if a is None:
            continue
        url = a.get("href")
        game_name = a.get_text(strip=True)
        players_el = el.select_one("td:first-child .currentServers")
        current_players = players_el.get_text(strip=True) if players_el else ""
        if not url or not game_name or not current_players:
            continue
        items.append(
            NewsItem(
                id=str(url),
                title=game_name,
                url=str(url),
                pub_date=now,
                extra=NewsExtra(info=current_players),
            )
        )
    return items
