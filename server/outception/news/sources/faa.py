"""FAA NASSTATUS — airport ground stops, ground delays, and closures."""

from bs4 import BeautifulSoup, Tag

from ..fetch import fetch_text
from ..registry import source
from ..schemas import NewsExtra, NewsItem

_URL = "https://nasstatus.faa.gov/api/airport-status-information"
_HOME = "https://nasstatus.faa.gov/"


def _delay_info(tag: Tag) -> str | None:
    avg = tag.find("Avg")
    max_ = tag.find("Max")
    parts: list[str] = []
    if avg and avg.get_text(strip=True):
        parts.append(f"avg {avg.get_text(strip=True)} min")
    if max_ and max_.get_text(strip=True):
        parts.append(f"max {max_.get_text(strip=True)} min")
    return ", ".join(parts) or None


@source("faadelays")
async def faadelays() -> list[NewsItem]:
    text = await fetch_text(_URL)
    soup = BeautifulSoup(text, "xml")
    items: list[NewsItem] = []

    for delay_type in soup.find_all("Delay_type"):
        name_tag = delay_type.find("Name")
        delay_name = name_tag.get_text(strip=True) if name_tag else ""

        if delay_name == "Ground Stop":
            for prog in delay_type.find_all("Program"):
                arpt = prog.find("ARPT")
                if not arpt:
                    continue
                airport_code = arpt.get_text(strip=True)
                reason_tag = prog.find("Reason")
                reason = (
                    reason_tag.get_text(strip=True).lower()
                    if reason_tag
                    else "ground stop"
                )
                items.append(
                    NewsItem(
                        id=f"{airport_code}-ground-stop",
                        title=f"{airport_code} — Ground Stop ({reason})",
                        url=_HOME,
                        extra=NewsExtra(info=_delay_info(prog)),
                    )
                )

        elif delay_name == "Ground Delay":
            for gd in delay_type.find_all("Ground_Delay"):
                arpt = gd.find("ARPT")
                if not arpt:
                    continue
                airport_code = arpt.get_text(strip=True)
                reason_tag = gd.find("Reason")
                reason = (
                    reason_tag.get_text(strip=True).lower()
                    if reason_tag
                    else "ground delay"
                )
                items.append(
                    NewsItem(
                        id=f"{airport_code}-ground-delay",
                        title=f"{airport_code} — Ground Delay ({reason})",
                        url=_HOME,
                        extra=NewsExtra(info=_delay_info(gd)),
                    )
                )

        elif delay_name == "Airport Closures":
            for cl in delay_type.find_all("Airport"):
                arpt = cl.find("ARPT")
                if not arpt:
                    continue
                airport_code = arpt.get_text(strip=True)
                reopen_tag = cl.find("Reopen")
                info = (
                    f"reopens {reopen_tag.get_text(strip=True)}" if reopen_tag else None
                )
                items.append(
                    NewsItem(
                        id=f"{airport_code}-closure",
                        title=f"{airport_code} — Airport Closure",
                        url=_HOME,
                        extra=NewsExtra(info=info),
                    )
                )

    return items
