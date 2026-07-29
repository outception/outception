from typing import TYPE_CHECKING, Any, Literal, cast

import redis as _sync_redis
import redis.asyncio as _async_redis
from fastapi import Request
from redis import ConnectionError, RedisError, TimeoutError
from redis.asyncio.retry import Retry
from redis.backoff import default_backoff

from outception.config import settings

# https://github.com/python/typeshed/issues/7597#issuecomment-1117551641
# Redis is generic at type checking, but not at runtime...
if TYPE_CHECKING:
    Redis = _async_redis.Redis[str]
else:
    Redis = _async_redis.Redis


REDIS_RETRY_ON_ERRROR: list[type[RedisError]] = [ConnectionError, TimeoutError]
# 50 retries against the 0.512s backoff cap is ~15-25s of sleeping per command.
# The rate-limit middleware runs a Redis command on EVERY request, so a brief
# Redis restart parked every inbound request for ~25s - thousands of live ASGI
# tasks, and a recovery far longer than the outage. Request-path clients fail
# fast; the worker keeps the patient retry, where blocking is the right answer.
REDIS_RETRY = Retry(default_backoff(), retries=3)
REDIS_RETRY_WORKER = Retry(default_backoff(), retries=50)

type ProcessName = Literal["app", "rate-limit", "worker", "script"]


def create_redis(process_name: ProcessName) -> Redis:
    # Bounded per process: the default pool grows without limit, so a request
    # stampede could walk a worker straight into Redis' maxclients and take
    # every other process down with it. It must be the BLOCKING pool: the
    # plain pool raises an UNRETRIED ConnectionError the moment connection
    # 257 is asked for (the pool hands out connections before the retry
    # wrapper runs), which would turn exactly the burst this bound exists to
    # survive into instant 500s. Blocking callers just wait for a slot.
    # decode_responses=True makes this Redis[str] at runtime; the pool type
    # is not generic, so the return needs the cast the from_url path got for
    # free from the TYPE_CHECKING alias above.
    pool: _async_redis.BlockingConnectionPool[Any] = (
        _async_redis.BlockingConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            retry_on_error=REDIS_RETRY_ON_ERRROR,
            retry=REDIS_RETRY_WORKER if process_name == "worker" else REDIS_RETRY,
            client_name=f"{settings.ENV.value}.{process_name}",
            max_connections=256,
            timeout=10,
        )
    )
    return cast(Redis, _async_redis.Redis(connection_pool=pool))


def create_sync_redis(process_name: ProcessName) -> "_sync_redis.Redis[str]":
    """Blocking client for the APScheduler main loop, which is not async."""
    # No retry policy: REDIS_RETRY is an asyncio Retry and the caller (the
    # scheduler heartbeat) treats a failed publish as non-fatal anyway - a
    # missed beat just means the next one lands.
    return _sync_redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=5,
        client_name=f"{settings.ENV.value}.{process_name}",
    )


async def get_redis(request: Request) -> Redis:
    return request.state.redis


__all__ = [
    "REDIS_RETRY",
    "REDIS_RETRY_ON_ERRROR",
    "REDIS_RETRY_WORKER",
    "Redis",
    "create_redis",
    "create_sync_redis",
    "get_redis",
]
