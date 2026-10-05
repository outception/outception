from urllib.parse import parse_qs

import pytest
import respx
from httpx import Response
from pytest_mock import MockerFixture

from outception.auth.turnstile import verify_turnstile
from outception.config import settings
from outception.exceptions import NotPermitted


@pytest.mark.asyncio
class TestVerifyTurnstile:
    async def test_success(
        self, respx_mock: respx.MockRouter, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TURNSTILE_SECRET", "secret")
        route = respx_mock.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        ).mock(return_value=Response(200, json={"success": True}))

        await verify_turnstile("test-token", "203.0.113.1")

        request = route.calls.last.request
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        payload = parse_qs(request.content.decode())
        assert payload["response"] == ["test-token"]
        assert payload["remoteip"] == ["203.0.113.1"]

    async def test_failure(
        self, respx_mock: respx.MockRouter, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TURNSTILE_SECRET", "secret")
        respx_mock.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        ).mock(return_value=Response(200, json={"success": False}))

        with pytest.raises(NotPermitted):
            await verify_turnstile("invalid-token", "203.0.113.1")

    async def test_missing_token_fails_when_configured(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TURNSTILE_SECRET", "secret")
        with pytest.raises(NotPermitted):
            await verify_turnstile(None, "203.0.113.1")

    async def test_no_secret_means_no_check(
        self, respx_mock: respx.MockRouter, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TURNSTILE_SECRET", "")
        route = respx_mock.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        ).mock(return_value=Response(200, json={"success": False}))
        await verify_turnstile(None, "203.0.113.1")
        await verify_turnstile("anything", "203.0.113.1")
        assert not route.called
