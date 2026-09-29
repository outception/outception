from fastapi import APIRouter, Depends, Response

from outception.openapi import APITag
from outception.redis import Redis, get_redis

from . import service
from .schemas import PromotedSlot

router = APIRouter(prefix="/promoted", tags=["promoted"])


@router.get(
    "/active",
    response_model=PromotedSlot | None,
    response_model_exclude_none=True,
    tags=[APITag.public],
)
async def get_active_slot(
    response: Response, redis: Redis = Depends(get_redis)
) -> PromotedSlot | None:
    """The Promoted card currently running, if any. At most one slot is ever
    active; the cards renders at most one Promoted card per serve. Cacheable
    for a short window - a run starting or ending reaches readers within a
    minute, which is plenty for time-boxed runs measured in hours or days."""
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=60"
    response.headers["Vary"] = "Origin"
    return await service.get_active(redis)
