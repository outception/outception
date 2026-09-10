"""HttpMetricsMiddleware tests. Self-contained: no app, database or broker."""

import asyncio
import os
import tempfile
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from starlette.types import Receive, Scope, Send


@pytest.fixture(scope="module", autouse=True)
def prometheus_tmpdir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmpdir
        yield tmpdir


async def noop_send(message: dict[str, Any]) -> None:
    pass


def respond(status: int) -> Any:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": status})
        await send({"type": "http.response.body", "body": b""})

    return app


def http_scope(path: str, method: str | None = "GET", **extra: Any) -> Scope:
    scope: dict[str, Any] = {"type": "http", "path": path, **extra}
    if method is not None:
        scope["method"] = method
    return cast(Scope, scope)


def run(middleware: Any, scope: Scope, send: Any = noop_send) -> None:
    asyncio.run(middleware(scope, cast(Receive, None), cast(Send, send)))


def route(path: str) -> MagicMock:
    mock_route = MagicMock()
    mock_route.path = path
    return mock_route


class TestScopeHandling:
    @pytest.mark.parametrize(
        "scope",
        [{"type": "websocket", "path": "/ws"}, {"type": "lifespan"}],
    )
    def test_non_http_scope_passthrough(self, scope: dict[str, Any]) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        app_called = False

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal app_called
            app_called = True

        run(HttpMetricsMiddleware(app), cast(Scope, scope))
        assert app_called is True

    def test_response_messages_are_forwarded(self) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        sent: list[dict[str, Any]] = []

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        run(HttpMetricsMiddleware(respond(201)), http_scope("/v1/news", "POST"), send)
        assert any(m.get("status") == 201 for m in sent)

    def test_exception_propagates(self) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            run(HttpMetricsMiddleware(app), http_scope("/v1/news"))

    @pytest.mark.parametrize(
        "method", ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", None]
    )
    def test_any_method(self, method: str | None) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        run(HttpMetricsMiddleware(respond(200)), http_scope("/v1/test", method))

    @pytest.mark.parametrize(
        "status", [200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]
    )
    def test_any_status(self, status: int) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        sent: list[dict[str, Any]] = []

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        run(HttpMetricsMiddleware(respond(status)), http_scope("/v1/test"), send)
        assert any(m.get("status") == status for m in sent)


class TestRecordedMetrics:
    @pytest.fixture
    def metrics(self, mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
        total = mocker.patch(
            "outception.observability.http_middleware.HTTP_REQUEST_TOTAL"
        )
        duration = mocker.patch(
            "outception.observability.http_middleware.HTTP_REQUEST_DURATION_SECONDS"
        )
        return total, duration

    def test_labels_use_route_template(
        self, metrics: tuple[MagicMock, MagicMock]
    ) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        total, duration = metrics
        scope = http_scope(
            "/v1/news/550e8400-e29b-41d4-a716-446655440000",
            "GET",
            route=route("/v1/news/{id}"),
        )
        run(HttpMetricsMiddleware(respond(200)), scope)

        total.labels.assert_called_once_with(
            endpoint="/v1/news/{id}", method="GET", status_code="200"
        )
        total.labels().inc.assert_called_once()
        duration.labels.assert_called_once_with(endpoint="/v1/news/{id}", method="GET")
        observed = duration.labels().observe.call_args[0][0]
        assert observed >= 0

    def test_missing_method_is_unknown(
        self, metrics: tuple[MagicMock, MagicMock]
    ) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        total, _ = metrics
        scope = http_scope("/v1/test", None, route=route("/v1/test"))
        run(HttpMetricsMiddleware(respond(200)), scope)

        total.labels.assert_called_once_with(
            endpoint="/v1/test", method="UNKNOWN", status_code="200"
        )

    def test_exception_before_response_records_500(
        self, metrics: tuple[MagicMock, MagicMock]
    ) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        total, _ = metrics

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            raise RuntimeError("crash")

        scope = http_scope("/v1/test", "GET", route=route("/v1/test"))
        with pytest.raises(RuntimeError):
            run(HttpMetricsMiddleware(app), scope)

        total.labels.assert_called_once_with(
            endpoint="/v1/test", method="GET", status_code="500"
        )

    @pytest.mark.parametrize("path", ["/healthz", "/healthz/deep", "/readyz"])
    def test_deny_listed_path_records_nothing(
        self, metrics: tuple[MagicMock, MagicMock], path: str
    ) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        total, duration = metrics
        run(HttpMetricsMiddleware(respond(200)), http_scope(path, route=route(path)))

        total.labels.assert_not_called()
        duration.labels.assert_not_called()

    def test_unmatched_route_records_nothing(
        self, metrics: tuple[MagicMock, MagicMock]
    ) -> None:
        from outception.observability.http_middleware import HttpMetricsMiddleware

        total, duration = metrics
        run(HttpMetricsMiddleware(respond(404)), http_scope("/v1/unknown"))

        total.labels.assert_not_called()
        duration.labels.assert_not_called()
