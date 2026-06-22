import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Any

import logfire
import structlog
import uvicorn
from dramatiq.middleware import Middleware
from redis import RedisError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from polar.config import settings
from polar.kit.db.postgres import create_async_sessionmaker
from polar.logfire import configure_logfire
from polar.logging import Logger
from polar.logging import configure as configure_logging
from polar.postgres import create_async_engine, create_async_read_engine
from polar.redis import Redis, create_redis

log: Logger = structlog.get_logger()

HTTP_HOST = os.getenv("dramatiq_prom_host", "0.0.0.0")
HTTP_PORT = int(os.getenv("dramatiq_prom_port", "9191"))

_heartbeat_checker: Callable[[], bool] | None = None


def set_heartbeat_checker(checker: Callable[[], bool]) -> None:
    global _heartbeat_checker
    _heartbeat_checker = checker


class HealthMiddleware(Middleware):
    @property
    def forks(self) -> list[Callable[[], int]]:
        return [_run_exposition_server]


async def health(request: Request) -> JSONResponse:
    try:
        redis: Redis = request.state.redis
        await redis.ping()
    except RedisError as e:
        raise HTTPException(status_code=503, detail="Redis is not available") from e

    if _heartbeat_checker is not None and not _heartbeat_checker():
        raise HTTPException(status_code=503, detail="Scheduler heartbeat is stale")

    return JSONResponse({"status": "ok"})


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[Mapping[str, Any]]:
    if settings.is_read_replica_configured():
        async_engine = create_async_read_engine("worker")
    else:
        async_engine = create_async_engine("worker")
    async_sessionmaker = create_async_sessionmaker(async_engine)
    redis = create_redis("worker")

    yield {
        "redis": redis,
        "async_sessionmaker": async_sessionmaker,
    }

    await redis.close()
    await async_engine.dispose()


async def handle_server_error(request: Request, exc: Exception) -> JSONResponse:
    logfire.exception(f"Worker health server error on {request.url.path}")
    return JSONResponse({"status": "error"}, status_code=500)


def create_app() -> Starlette:
    routes = [
        Route("/", health, methods=["GET"]),
    ]
    return Starlette(
        routes=routes,
        lifespan=lifespan,
        exception_handlers={Exception: handle_server_error},
    )


def _run_exposition_server() -> int:
    log.debug("Starting exposition server...")
    configure_logfire("worker")
    configure_logging(logfire=True)
    app = create_app()
    config = uvicorn.Config(
        app, host=HTTP_HOST, port=HTTP_PORT, log_level="error", access_log=False
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except asyncio.CancelledError:
        pass

    return 0
