import os
import socket

from fastapi import Depends, HTTPException
from redis import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

router = APIRouter(tags=["health"], include_in_schema=False)

# Memoized database probe verdict. Uptime probes and the container health
# check each poll every few seconds, and every uncached probe checks a
# connection out of the pool — cache the verdict briefly so the probes
# collectively cost one pool checkout per window instead of one each.
# Scoped PER PROCESS: /healthz is a liveness probe for THIS container, and the
# deploy gate rolls back on it. A fleet-wide key let a new container inherit
# the outgoing one's "ok" and pass the gate without ever touching its own
# engine — exactly the bad-config rollout the gate exists to catch.
_DB_PROBE_KEY = f"healthz:db:{socket.gethostname()}:{os.getpid()}"
_DB_PROBE_TTL_SECONDS = 5
_DB_PROBE_OK = "ok"
_DB_PROBE_DOWN = "down"


@router.get("/healthz")
async def healthz(
    session: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis)
) -> dict[str, str]:
    # The cache read doubles as the Redis probe — no separate ping needed.
    try:
        verdict = await redis.get(_DB_PROBE_KEY)
    except RedisError as e:
        raise HTTPException(status_code=503, detail="Redis is not available") from e

    if verdict is None:
        try:
            await session.execute(select(1))
        except SQLAlchemyError:
            verdict = _DB_PROBE_DOWN
        else:
            verdict = _DB_PROBE_OK
        try:
            await redis.set(_DB_PROBE_KEY, verdict, ex=_DB_PROBE_TTL_SECONDS)
        except RedisError as e:
            raise HTTPException(status_code=503, detail="Redis is not available") from e

    if verdict != _DB_PROBE_OK:
        raise HTTPException(status_code=503, detail="Database is not available")

    return {"status": "ok"}
