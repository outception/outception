import socket

import pytest
from pytest_mock import MockerFixture

from outception.net.guard import (
    _host_to_resolve,
    extract_urls,
    is_fetchable,
    is_fetchable_async,
    sanitize_image_url,
)


def _infos(*addresses: str) -> list[tuple[object, ...]]:
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))
        for address in addresses
    ]


class TestHostToResolve:
    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/x",
            "javascript:alert(1)",
            "http:///nohost",
            "http://169.254.169.254/latest",
            "http://metadata.google.internal/",
        ],
    )
    def test_rejected_before_dns(self, url: str) -> None:
        assert _host_to_resolve(url) is None

    def test_http_host(self) -> None:
        assert _host_to_resolve("https://Example.com/path") == "example.com"


class TestIsFetchable:
    @pytest.mark.parametrize(
        "address",
        ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.10.10", "::1", "fd00::1"],
    )
    def test_private_ranges_rejected(self, mocker: MockerFixture, address: str) -> None:
        mocker.patch("socket.getaddrinfo", return_value=_infos(address))
        assert is_fetchable("https://example.com/") is False

    def test_mixed_resolution_rejected(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "socket.getaddrinfo", return_value=_infos("93.184.216.34", "10.0.0.1")
        )
        assert is_fetchable("https://example.com/") is False

    def test_public_accepted(self, mocker: MockerFixture) -> None:
        mocker.patch("socket.getaddrinfo", return_value=_infos("93.184.216.34"))
        assert is_fetchable("https://example.com/") is True

    def test_dns_failure_rejected(self, mocker: MockerFixture) -> None:
        mocker.patch("socket.getaddrinfo", side_effect=socket.gaierror)
        assert is_fetchable("https://nope.invalid/") is False

    @pytest.mark.asyncio
    async def test_async_twin(self, mocker: MockerFixture) -> None:
        mocker.patch("anyio.getaddrinfo", return_value=_infos("93.184.216.34"))
        assert await is_fetchable_async("https://example.com/") is True
        mocker.patch("anyio.getaddrinfo", return_value=_infos("127.0.0.1"))
        assert await is_fetchable_async("https://example.com/") is False


class TestHelpers:
    def test_extract_urls(self) -> None:
        text = "see https://a.example/x. and (https://b.example/y), again https://a.example/x"
        assert extract_urls(text) == ["https://a.example/x", "https://b.example/y"]

    def test_sanitize_image_url(self, mocker: MockerFixture) -> None:
        mocker.patch("socket.getaddrinfo", return_value=_infos("93.184.216.34"))
        assert (
            sanitize_image_url("/logo.png", "https://example.com/page")
            == "https://example.com/logo.png"
        )
        assert sanitize_image_url("", "https://example.com/page") is None
        assert sanitize_image_url("javascript:alert(1)", "https://example.com/") is None
