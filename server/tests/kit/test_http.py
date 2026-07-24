import socket
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from starlette.requests import Request

from outception.config import settings
from outception.kit.http import (
    SSRFBlockedError,
    check_url_reachable,
    get_ip_address,
    get_safe_return_url,
    resolve_and_validate_ip,
)


def _request(peer: str | None, headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": (peer, 12345) if peer else None,
        }
    )


class TestGetIpAddress:
    def test_ignores_header_from_untrusted_peer(self) -> None:
        with patch.object(settings, "TRUSTED_PROXY_IPS", ["172.16.0.0/12"]):
            req = _request("203.0.113.9", {"CF-Connecting-IP": "1.2.3.4"})
            assert get_ip_address(req) == "203.0.113.9"

    def test_honours_cf_connecting_ip_from_trusted_peer(self) -> None:
        with patch.object(settings, "TRUSTED_PROXY_IPS", ["172.16.0.0/12"]):
            req = _request("172.20.0.5", {"CF-Connecting-IP": "1.2.3.4"})
            assert get_ip_address(req) == "1.2.3.4"

    def test_falls_back_to_peer_when_no_accepted_header(self) -> None:
        # X-Forwarded-For alone (the CF->Caddy edge doesn't emit True-Client-IP)
        # is not in the accepted list, so we use the socket peer, not a
        # spoofable XFF entry.
        with patch.object(settings, "TRUSTED_PROXY_IPS", ["172.16.0.0/12"]):
            req = _request("172.20.0.5", {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
            assert get_ip_address(req) == "172.20.0.5"

    def test_never_trusts_header_without_configured_proxies(self) -> None:
        with patch.object(settings, "TRUSTED_PROXY_IPS", []):
            req = _request("172.20.0.5", {"CF-Connecting-IP": "1.2.3.4"})
            assert get_ip_address(req) == "172.20.0.5"

    def test_header_priority_and_comma_list(self) -> None:
        with patch.object(settings, "TRUSTED_PROXY_IPS", ["172.16.0.0/12"]):
            req = _request(
                "172.20.0.5",
                {"CF-Connecting-IP": "1.2.3.4, 9.9.9.9", "True-Client-IP": "8.8.8.8"},
            )
            assert get_ip_address(req) == "1.2.3.4"


@pytest.mark.asyncio
async def test_get_safe_return_url() -> None:
    assert get_safe_return_url("/foo") == "http://127.0.0.1:3000/foo"

    assert (
        get_safe_return_url("http://127.0.0.1:3000/foo") == "http://127.0.0.1:3000/foo"
    )

    assert get_safe_return_url("") == "http://127.0.0.1:3000/"

    assert get_safe_return_url("https://whatever.com/hey") == "http://127.0.0.1:3000/"


def _fake_getaddrinfo(*addrs: str) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    """Build a fake getaddrinfo result list from IP strings."""
    return [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, 0))
        for a in addrs
    ]


class TestResolveAndValidateIp:
    @pytest.mark.asyncio
    async def test_blocks_loopback(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("127.0.0.1")),
        ):
            with pytest.raises(SSRFBlockedError, match="private/reserved"):
                await resolve_and_validate_ip("localhost")

    @pytest.mark.asyncio
    async def test_blocks_private_10x(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("10.0.0.1")),
        ):
            with pytest.raises(SSRFBlockedError):
                await resolve_and_validate_ip("internal.example.com")

    @pytest.mark.asyncio
    async def test_blocks_private_172_16(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("172.16.0.1")),
        ):
            with pytest.raises(SSRFBlockedError):
                await resolve_and_validate_ip("internal.example.com")

    @pytest.mark.asyncio
    async def test_blocks_private_192_168(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("192.168.1.1")),
        ):
            with pytest.raises(SSRFBlockedError):
                await resolve_and_validate_ip("internal.example.com")

    @pytest.mark.asyncio
    async def test_blocks_link_local_metadata(self) -> None:
        """169.254.169.254 (AWS/GCP metadata) is link-local and must be blocked."""
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("169.254.169.254")),
        ):
            with pytest.raises(SSRFBlockedError, match="private/reserved"):
                await resolve_and_validate_ip("metadata.internal")

    @pytest.mark.asyncio
    async def test_blocks_ipv6_loopback(self) -> None:
        info = [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 0, 0, 0),
            )
        ]
        with patch("anyio.getaddrinfo", new=AsyncMock(return_value=info)):
            with pytest.raises(SSRFBlockedError):
                await resolve_and_validate_ip("localhost6")

    @pytest.mark.asyncio
    async def test_allows_public_ip(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("93.184.216.34")),
        ):
            # Should not raise
            await resolve_and_validate_ip("example.com")

    @pytest.mark.asyncio
    async def test_blocks_mixed_public_and_private(self) -> None:
        """If even one resolved IP is private, the request must be blocked."""
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("93.184.216.34", "10.0.0.1")),
        ):
            with pytest.raises(SSRFBlockedError):
                await resolve_and_validate_ip("dual-homed.example.com")

    @pytest.mark.asyncio
    async def test_dns_failure(self) -> None:
        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(side_effect=OSError("NXDOMAIN")),
        ):
            with pytest.raises(SSRFBlockedError, match="DNS resolution failed"):
                await resolve_and_validate_ip("nonexistent.invalid")


@contextmanager
def _mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Iterator[None]:
    """Patch the client used by `check_url_reachable` to route through a mock."""
    real_async_client = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        return real_async_client(transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]

    with patch("outception.kit.http.httpx.AsyncClient", new=factory):
        yield


class TestCheckUrlReachable:
    @pytest.mark.asyncio
    async def test_follows_relative_redirect_location(self) -> None:
        """A relative `Location` (e.g. `/login`) must be resolved, not rejected.

        A relative location previously failed `HttpUrl` parsing and wrongly
        marked the site unreachable; it must be resolved against the request
        URL before being followed.
        """

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == "https://example.com/":
                # Relative location — resolved against the request URL.
                return httpx.Response(307, headers={"location": "/login"})
            if url == "https://example.com/login":
                return httpx.Response(200)
            raise AssertionError(f"unexpected URL: {url}")

        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("93.184.216.34")),
        ):
            with _mock_transport(handler):
                result = await check_url_reachable("https://example.com")

        assert result.reachable is True
        assert result.status == 200

    @pytest.mark.asyncio
    async def test_blocks_redirect_to_private_host(self) -> None:
        """SSRF protection still holds: a redirect to a private IP is blocked."""

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == "https://example.com/":
                return httpx.Response(
                    302, headers={"location": "https://internal.example.com/"}
                )
            raise AssertionError(f"should not follow redirect to {request.url}")

        async def fake_getaddrinfo(
            host: str, *args: object, **kwargs: object
        ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
            if host == "internal.example.com":
                return _fake_getaddrinfo("10.0.0.1")
            return _fake_getaddrinfo("93.184.216.34")

        with patch("anyio.getaddrinfo", new=fake_getaddrinfo):
            with _mock_transport(handler):
                result = await check_url_reachable("https://example.com")

        assert result.reachable is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_malformed_redirect_location(self) -> None:
        """A malformed `Location` (e.g. invalid port) is unreachable, not a 500.

        `response.url.join(location)` raises `httpx.InvalidURL` for such
        headers; since that isn't an `httpx.HTTPError`, it must be converted
        to a graceful `reachable=False` result rather than escaping.
        """

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == "https://example.com/":
                return httpx.Response(
                    302, headers={"location": "https://example.com:abc/login"}
                )
            raise AssertionError(f"should not follow redirect to {request.url}")

        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("93.184.216.34")),
        ):
            with _mock_transport(handler):
                result = await check_url_reachable("https://example.com")

        assert result.reachable is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_unreachable_on_4xx(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        with patch(
            "anyio.getaddrinfo",
            new=AsyncMock(return_value=_fake_getaddrinfo("93.184.216.34")),
        ):
            with _mock_transport(handler):
                result = await check_url_reachable("https://example.com")

        assert result.reachable is False
        assert result.status == 404
