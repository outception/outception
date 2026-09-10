import json
from collections.abc import Sequence
from typing import Any

import httpx
import structlog

from outception.config import settings
from outception.logging import Logger

log: Logger = structlog.get_logger()


class TinybirdClient:
    """Thin client for the Tinybird Events API.

    Pushes JSON events to a datasource via the high-frequency ingestion endpoint
    (``POST /v0/events?name=<datasource>``) as newline-delimited JSON. Ingestion
    is best-effort: when Tinybird isn't configured the client is a no-op, and
    transport errors are logged rather than raised so analytics never breaks the
    feature that emits the events.
    """

    async def send_events(
        self, datasource: str, events: Sequence[dict[str, Any]]
    ) -> None:
        if not events or not settings.is_tinybird_configured():
            return

        ndjson = "\n".join(json.dumps(event, default=str) for event in events)
        try:
            async with httpx.AsyncClient(
                base_url=settings.TINYBIRD_API_URL,
                headers={"Authorization": f"Bearer {settings.TINYBIRD_API_TOKEN}"},
                timeout=10.0,
            ) as client:
                response = await client.post(
                    "/v0/events",
                    params={"name": datasource},
                    content=ndjson,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.warning(
                "tinybird.send_events.failed",
                datasource=datasource,
                count=len(events),
                error=str(e),
            )

    async def query_pipe(
        self, pipe: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Query a published Tinybird pipe endpoint and return its ``data`` rows.

        Reads with the read token when available (falling back to the admin
        token). Raises ``httpx.HTTPError`` on transport/HTTP failures so callers
        can fall back to another source.
        """
        token = settings.TINYBIRD_READ_TOKEN or settings.TINYBIRD_API_TOKEN
        async with httpx.AsyncClient(
            base_url=settings.TINYBIRD_API_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        ) as client:
            response = await client.get(
                f"/v0/pipes/{pipe}.json",
                params={k: v for k, v in params.items() if v is not None},
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            return list(data)


tinybird_client = TinybirdClient()
