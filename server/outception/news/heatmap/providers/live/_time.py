"""Shared time helpers for the live tiles: ages and countdowns as the
label reads them."""

from datetime import UTC, datetime


def now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def age_label(then_ms: int, now: int | None = None) -> str:
    """ "just now", "12 min ago", "3 h ago", "2 d ago"."""
    now = now_ms() if now is None else now
    seconds = max(0, (now - then_ms) // 1000)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"


def countdown_label(then_ms: int, now: int | None = None) -> str:
    """ "in 4 min", "in 3 h 10 min", "in 2 d 5 h"; "now" once passed."""
    now = now_ms() if now is None else now
    seconds = (then_ms - now) // 1000
    if seconds <= 0:
        return "now"
    if seconds < 3600:
        return f"in {max(1, seconds // 60)} min"
    if seconds < 86400:
        hours, minutes = divmod(seconds // 60, 60)
        return f"in {hours} h {minutes} min" if minutes else f"in {hours} h"
    days, hours = divmod(seconds // 3600, 24)
    return f"in {days} d {hours} h" if hours else f"in {days} d"
