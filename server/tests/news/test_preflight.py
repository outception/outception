"""CORS preflight must survive the full middleware stack.

Regression guard for the 2026-09-06 outage class: a framework upgrade broke a
tracing library on requests that PARTIALLY match a route - which is exactly
what a browser OPTIONS preflight does (path matches, method doesn't) - so
every preflighted call 500'd and the web wall showed "failed to load" while
plain GETs (and therefore every health check) stayed green. An OPTIONS
request through the real app is the only thing that exercises that path.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCorsPreflight:
    async def test_get_preflight_returns_200(self, client: AsyncClient) -> None:
        response = await client.options(
            "/v1/news/sources",
            headers={
                "Origin": "https://outception.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    async def test_post_preflight_with_headers_returns_200(
        self, client: AsyncClient
    ) -> None:
        response = await client.options(
            "/v1/news/batch",
            headers={
                "Origin": "https://outception.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
