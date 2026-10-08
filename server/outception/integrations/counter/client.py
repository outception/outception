"""The PostHog Query API: one HogQL query per call, bearer token, JSON."""

import httpx

from outception.config import settings

from .exceptions import CounterError, CounterNotConfigured

_client = httpx.AsyncClient(timeout=30.0)


def configured() -> bool:
    return bool(settings.POSTHOG_API_KEY and settings.POSTHOG_PROJECT_ID)


async def query(hogql: str, *, name: str) -> list[list[object]]:
    """Run one HogQL query and return its rows (a list per row). The
    project limits are 240 queries a minute and ten seconds per query;
    the hourly sync sends two."""
    if not configured():
        raise CounterNotConfigured()
    url = (
        f"{settings.POSTHOG_HOST.rstrip('/')}/api/projects/"
        f"{settings.POSTHOG_PROJECT_ID}/query/"
    )
    try:
        response = await _client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.POSTHOG_API_KEY}",
                "content-type": "application/json",
            },
            json={"query": {"kind": "HogQLQuery", "query": hogql}, "name": name},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise ValueError("no results in the reply")
        return [list(row) for row in results if isinstance(row, list | tuple)]
    except (httpx.HTTPError, ValueError) as exc:
        raise CounterError(str(exc)) from exc
