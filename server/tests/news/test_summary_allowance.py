from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from outception.redis import Redis


@pytest.mark.asyncio
class TestSummaryAllowance:
    async def test_cached_is_free_and_new_ones_are_counted(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from starlette.requests import Request

        from outception.news import endpoints

        request = Request(
            {"type": "http", "headers": [], "client": ("203.0.113.9", 1234)}
        )
        mocker.patch.object(endpoints, "_CLIENT_HOURLY_SUMMARIES", 2)
        mocker.patch(
            "outception.news.endpoints.summaries.has_cached",
            AsyncMock(side_effect=[True, False, False, False]),
        )
        url = "https://example.com/article"
        assert await endpoints._charge_summary(redis, request, url) is True
        assert await endpoints._charge_summary(redis, request, url) is True
        assert await endpoints._charge_summary(redis, request, url) is True
        assert await endpoints._charge_summary(redis, request, url) is False
