from typing import Any

from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from redis import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

from .service import HealthService

router = APIRouter(tags=["health"], include_in_schema=False)


@router.get("/healthz")
async def healthz(
    session: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis)
) -> dict[str, str]:
    """The liveness check the deploy gate and the uptime monitor use."""
    try:
        await session.execute(select(1))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail="Database is not available") from e

    try:
        await redis.ping()
    except RedisError as e:
        raise HTTPException(status_code=503, detail="Redis is not available") from e

    return {"status": "ok"}


@router.get("/health")
async def health(
    session: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis)
) -> JSONResponse:
    """Health with reasons: every unhealthy condition as a stable code with
    its severity and remedy. 200 when ok or degraded, 503 when unhealthy."""
    report: dict[str, Any] = await HealthService(session, redis).report()
    status_code = 503 if report["status"] == "unhealthy" else 200
    return JSONResponse(report, status_code=status_code)
