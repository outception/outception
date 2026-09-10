import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from redis import RedisError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from outception.worker._health import (
    HEARTBEAT_STALENESS_SECONDS,
    handle_server_error,
    health,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    mock = AsyncMock()
    mock.ping = AsyncMock()
    # No heartbeat published: the scheduler may not be part of this deployment.
    mock.get = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_request(mock_redis: AsyncMock) -> MagicMock:
    req = MagicMock()
    req.state.redis = mock_redis
    return req


@pytest.mark.asyncio
class TestHealth:
    async def test_healthy_without_published_heartbeat(
        self, mock_request: MagicMock, mock_redis: AsyncMock
    ) -> None:
        response = await health(mock_request)
        assert response.status_code == 200
        mock_redis.ping.assert_called_once()

    async def test_healthy_with_recent_heartbeat(
        self, mock_request: MagicMock, mock_redis: AsyncMock
    ) -> None:
        mock_redis.get.return_value = str(time.time())
        response = await health(mock_request)
        assert response.status_code == 200

    async def test_unhealthy_with_stale_heartbeat(
        self, mock_request: MagicMock, mock_redis: AsyncMock
    ) -> None:
        mock_redis.get.return_value = str(time.time() - HEARTBEAT_STALENESS_SECONDS - 1)
        with pytest.raises(HTTPException) as exc_info:
            await health(mock_request)
        assert exc_info.value.status_code == 503
        assert "heartbeat" in str(exc_info.value.detail).lower()

    async def test_healthy_with_unparseable_heartbeat(
        self, mock_request: MagicMock, mock_redis: AsyncMock
    ) -> None:
        # A corrupt value must not take the worker out of rotation.
        mock_redis.get.return_value = "not-a-timestamp"
        response = await health(mock_request)
        assert response.status_code == 200

    async def test_redis_unavailable(
        self, mock_request: MagicMock, mock_redis: AsyncMock
    ) -> None:
        mock_redis.ping.side_effect = RedisError("Connection refused")

        with pytest.raises(HTTPException) as exc_info:
            await health(mock_request)

        assert exc_info.value.status_code == 503
        assert "Redis" in str(exc_info.value.detail)


def _create_test_app(heartbeat: str | None = None) -> Starlette:
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.get = AsyncMock(return_value=heartbeat)

    async def inject_state(request: Request, call_next: Any) -> JSONResponse:
        request.state.redis = mock_redis
        return await call_next(request)

    routes = [Route("/", health, methods=["GET"])]
    app = Starlette(
        routes=routes,
        exception_handlers={Exception: handle_server_error},
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=inject_state)
    return app


@pytest.mark.asyncio
class TestSchedulerHealthIntegration:
    async def test_healthy_with_recent_heartbeat(self) -> None:
        app = _create_test_app(heartbeat=str(time.time()))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    async def test_unhealthy_with_stale_heartbeat(self) -> None:
        app = _create_test_app(
            heartbeat=str(time.time() - HEARTBEAT_STALENESS_SECONDS - 1)
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.status_code == 503
            assert "heartbeat" in response.text.lower()

    async def test_workers_unaffected_without_scheduler(self) -> None:
        # A plain worker deployment publishes no heartbeat and must stay healthy.
        app = _create_test_app(heartbeat=None)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.status_code == 200
