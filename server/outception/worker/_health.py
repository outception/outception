import asyncio
import contextlib
import os
import time
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Any

import logfire
import structlog
import uvicorn
from dramatiq.middleware import Middleware
from redis import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from outception.kit.db.postgres import AsyncSessionMaker, create_async_sessionmaker
from outception.logfire import configure_logfire
from outception.logging import Logger
from outception.logging import configure as configure_logging
from outception.postgres import AsyncEngine, create_async_engine
from outception.redis import Redis, create_redis

log: Logger = structlog.get_logger()

HTTP_HOST = os.getenv("dramatiq_prom_host", "0.0.0.0")
HTTP_PORT = int(os.getenv("dramatiq_prom_port", "9191"))

# The scheduler runs in a different process from the one serving this endpoint,
# so its liveness has to travel through Redis. An in-process callback here was
# only ever registered in the scheduler process and could never be consulted by
# the broker fork that actually answers /healthz.
SCHEDULER_HEARTBEAT_KEY = "worker:scheduler:heartbeat"
HEARTBEAT_STALENESS_SECONDS = 60


async def _scheduler_heartbeat_is_stale(redis: Redis) -> bool:
    raw = await redis.get(SCHEDULER_HEARTBEAT_KEY)
    # Absent means the scheduler hasn't published yet (or isn't part of this
    # deployment) - not a failure. Only a heartbeat that has gone quiet is.
    if raw is None:
        return False
    try:
        return (time.time() - float(raw)) >= HEARTBEAT_STALENESS_SECONDS
    except ValueError:
        return False


class HealthMiddleware(Middleware):
    def __init__(self, *, database: bool = True) -> None:
        self._database = database

    @property
    def forks(self) -> list[Callable[[], int]]:
        if self._database:
            return [_run_exposition_server]
        return [_run_exposition_server_without_db]


async def health(request: Request) -> JSONResponse:
    try:
        redis: Redis = request.state.redis
        await redis.ping()
    except RedisError as e:
        raise HTTPException(status_code=503, detail="Redis is not available") from e

    async_sessionmaker: AsyncSessionMaker | None = getattr(
        request.state, "async_sessionmaker", None
    )
    if async_sessionmaker is not None:
        try:
            async with async_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503, detail="Database is not available"
            ) from e

    if await _scheduler_heartbeat_is_stale(redis):
        raise HTTPException(status_code=503, detail="Scheduler heartbeat is stale")

    return JSONResponse({"status": "ok"})


def _create_lifespan(
    *, database: bool
) -> Callable[[Starlette], contextlib.AbstractAsyncContextManager[Mapping[str, Any]]]:
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncGenerator[Mapping[str, Any]]:
        redis = create_redis("worker")
        state: dict[str, Any] = {"redis": redis}

        async_engine: AsyncEngine | None = None
        if database:
            async_engine = create_async_engine("worker")
            state["async_sessionmaker"] = create_async_sessionmaker(async_engine)

        yield state

        await redis.close()
        if async_engine is not None:
            await async_engine.dispose()

    return lifespan


async def handle_server_error(request: Request, exc: Exception) -> JSONResponse:
    logfire.exception(f"Worker health server error on {request.url.path}")
    return JSONResponse({"status": "error"}, status_code=500)


def create_app(*, database: bool = True) -> Starlette:
    routes = [Route("/", health, methods=["GET"])]
    return Starlette(
        routes=routes,
        lifespan=_create_lifespan(database=database),
        exception_handlers={Exception: handle_server_error},
    )


def _run_server(*, database: bool) -> int:
    log.debug("Starting exposition server...")
    configure_logfire("worker")
    configure_logging(logfire=True)
    app = create_app(database=database)
    config = uvicorn.Config(
        app, host=HTTP_HOST, port=HTTP_PORT, log_level="error", access_log=False
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except asyncio.CancelledError:
        pass

    return 0


def _run_exposition_server() -> int:
    return _run_server(database=True)


def _run_exposition_server_without_db() -> int:
    return _run_server(database=False)
