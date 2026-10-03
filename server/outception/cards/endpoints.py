"""One card contract: `GET /v1/cards/{id}` carries the envelope for a
feed, a table, a briefing or the weather strip, with the signal state
and the update stamp. The legacy routes keep serving their views."""

from fastapi import Depends, Header, Query, Request, Response

from outception.kit.http import get_ip_address
from outception.openapi import APITag
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

from . import service
from .schemas import Card

router = APIRouter(prefix="/cards", tags=["cards"])


def _ip_country(header: str | None) -> str | None:
    if not header:
        return None
    cc = header.strip().upper()
    return cc if len(cc) == 2 and cc not in {"XX", "T1", "EU", "AP"} else None


@router.get("/{card_id}", response_model=Card, tags=[APITag.public])
async def get_card(
    card_id: str,
    request: Request,
    response: Response,
    latest: bool = Query(False),
    country: str | None = Query(None, min_length=2, max_length=2),
    attached_to: str | None = Query(None, alias="attachedTo", max_length=128),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
    redis: Redis = Depends(get_redis),
) -> Card:
    """The card by id: a source id for a feed or a table, `briefing:<profile>`
    for a briefing, `weather` for the strip (with `attachedTo` naming the
    country or city card it rides on)."""
    card = await service.card_for(
        redis,
        card_id,
        country=(country or _ip_country(cf_ipcountry) or "").upper() or None,
        attached_to=attached_to,
        latest=latest,
        client=get_ip_address(request),
    )
    response.headers.update(service.cache_headers(card))
    return card
