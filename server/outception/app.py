import contextlib
from collections.abc import AsyncIterator
from typing import TypedDict

import structlog
from fastapi import FastAPI

from outception import worker  # noqa
from outception.api import router
from outception.auth.exception_handlers import (
    OutceptionAuthRedirectionError,
    auth_redirection_error_exception_handler,
)
from outception.auth.middlewares import AuthSubjectMiddleware
from outception.config import settings
from outception.exception_handlers import add_exception_handlers
from outception.health.endpoints import router as health_router
from outception.kit.cors import CORSConfig, CORSMatcherMiddleware, Scope
from outception.kit.db.postgres import (
    AsyncEngine,
    AsyncSessionMaker,
    Engine,
    SyncSessionMaker,
    create_async_sessionmaker,
    create_sync_sessionmaker,
)
from outception.kit.hash_secrets import get_hash_secrets
from outception.kit.http import HSTSMiddleware
from outception.kit.versioning import VERSION_HEADER, add_versioned_routers
from outception.logfire import (
    configure_logfire,
    instrument_fastapi,
    instrument_httpx,
    instrument_sqlalchemy,
)
from outception.logging import Logger
from outception.logging import configure as configure_logging
from outception.middlewares import (
    CacheControlMiddleware,
    LogCorrelationIdMiddleware,
    MaxBodySizeMiddleware,
    OperationalErrorMiddleware,
    PathRewriteMiddleware,
    SandboxResponseHeaderMiddleware,
    TransactionalMiddleware,
)
from outception.oauth2.endpoints.well_known import router as well_known_router
from outception.oauth2.exception_handlers import (
    OAuth2Error,
    oauth2_error_exception_handler,
)
from outception.observability.http_middleware import HttpMetricsMiddleware
from outception.observability.memory_profile import (
    start_memory_profiler,
    stop_memory_profiler,
)
from outception.observability.remote_write import (
    start_remote_write_pusher,
    stop_remote_write_pusher,
)
from outception.observability.slo import start_slo_metrics, stop_slo_metrics
from outception.postgres import (
    create_async_engine,
    create_async_read_engine,
    create_sync_engine,
)
from outception.redis import Redis, create_redis
from outception.sentry import configure_sentry
from outception.version import CURRENT_API_VERSION, VERSIONS

from . import rate_limit

log: Logger = structlog.get_logger()


def configure_cors(app: FastAPI) -> None:
    configs: list[CORSConfig] = []

    # Outception frontend CORS configuration
    if settings.CORS_ORIGINS:

        def outception_frontend_matcher(origin: str, scope: Scope) -> bool:
            return origin in settings.CORS_ORIGINS

        outception_frontend_config = CORSConfig(
            outception_frontend_matcher,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,  # Cookies are allowed, but only there!
            allow_methods=["*"],
            allow_headers=["*"],
        )
        configs.append(outception_frontend_config)

    # External API calls CORS configuration
    api_config = CORSConfig(
        lambda origin, scope: True,
        allow_origins=["*"],
        allow_credentials=False,  # No cookies allowed
        allow_methods=["*"],
        allow_headers=["Authorization", VERSION_HEADER],
        expose_headers=[VERSION_HEADER],
    )
    configs.append(api_config)

    app.add_middleware(CORSMatcherMiddleware, configs=configs)


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker
    async_read_engine: AsyncEngine
    async_read_sessionmaker: AsyncSessionMaker
    sync_engine: Engine
    sync_sessionmaker: SyncSessionMaker

    redis: Redis


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    log.info("Starting Outception API")

    # Fail the deploy on a misconfigured secret
    hash_secrets = get_hash_secrets()
    log.info("hash_secrets_loaded", current_secret_id=hash_secrets.current_id)

    # Start memory profiler (if configured)
    profiler_enabled = start_memory_profiler()
    if profiler_enabled:
        log.info("memory_profile_enabled")

    # Start HTTP metrics pusher (if configured)
    # Use include_queue_metrics=False since queue metrics are worker-specific
    metrics_enabled = start_remote_write_pusher(include_queue_metrics=False)
    if metrics_enabled:
        log.info("prometheus_remote_write_enabled")

    # Initialize SLO target metrics for critical endpoints (refreshed every 5 minutes)
    start_slo_metrics()

    async_engine = async_read_engine = create_async_engine("app")
    async_sessionmaker = async_read_sessionmaker = create_async_sessionmaker(
        async_engine
    )
    instrument_engines = [async_engine.sync_engine]

    if settings.is_read_replica_configured():
        async_read_engine = create_async_read_engine("app")
        async_read_sessionmaker = create_async_sessionmaker(async_read_engine)
        instrument_engines.append(async_read_engine.sync_engine)

    sync_engine = create_sync_engine("app")
    sync_sessionmaker = create_sync_sessionmaker(sync_engine)
    instrument_engines.append(sync_engine)
    instrument_sqlalchemy(instrument_engines)

    redis = create_redis("app")

    log.info("Outception API started")

    yield {
        "async_engine": async_engine,
        "async_sessionmaker": async_sessionmaker,
        "async_read_engine": async_read_engine,
        "async_read_sessionmaker": async_read_sessionmaker,
        "sync_engine": sync_engine,
        "sync_sessionmaker": sync_sessionmaker,
        "redis": redis,
    }

    # Stop background threads
    stop_memory_profiler()
    stop_slo_metrics()
    stop_remote_write_pusher()

    await redis.close(True)
    rate_limit_redis = getattr(app.state, "rate_limit_redis", None)
    if rate_limit_redis is not None:
        await rate_limit_redis.close(True)
    await async_engine.dispose()
    if async_read_engine is not async_engine:
        await async_read_engine.dispose()
    sync_engine.dispose()

    log.info("Outception API stopped")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, openapi_url=None)

    app.add_middleware(OperationalErrorMiddleware)
    if settings.is_sandbox():
        app.add_middleware(SandboxResponseHeaderMiddleware)
    if not settings.is_development() and not settings.is_testing():
        app.add_middleware(HSTSMiddleware)
    app.add_middleware(CacheControlMiddleware)
    if not settings.is_testing():
        rate_limit_redis = create_redis("rate-limit")
        app.state.rate_limit_redis = rate_limit_redis
        app.add_middleware(AuthSubjectMiddleware, redis=rate_limit_redis)
        app.add_middleware(TransactionalMiddleware)
        app.add_middleware(rate_limit.get_middleware, redis=rate_limit_redis)
    app.add_middleware(PathRewriteMiddleware, pattern=r"^/api/v1", replacement="/v1")
    app.add_middleware(LogCorrelationIdMiddleware)
    app.add_middleware(MaxBodySizeMiddleware, limit=settings.API_MAX_REQUEST_BODY_SIZE)
    if not settings.is_testing():
        app.add_middleware(HttpMetricsMiddleware)

    configure_cors(app)

    add_exception_handlers(app)
    app.add_exception_handler(OAuth2Error, oauth2_error_exception_handler)
    app.add_exception_handler(
        OutceptionAuthRedirectionError, auth_redirection_error_exception_handler
    )

    # /.well-known: OAuth2 and OIDC discovery, JWKS and the Apple domain
    # association. All of it is account machinery, so it follows the same gate
    # as the auth routers: with accounts off it must not exist.
    if settings.ACCOUNTS_ENABLED:
        app.include_router(well_known_router)

    # /healthz
    app.include_router(health_router)

    add_versioned_routers(app, router, [], VERSIONS, CURRENT_API_VERSION)

    return app


configure_sentry()
configure_logfire("server")
configure_logging(logfire=True)

app = create_app()
instrument_fastapi(app)
instrument_httpx()
