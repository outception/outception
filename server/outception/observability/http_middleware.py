"""ASGI middleware recording request count and duration per route template."""

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from outception.observability.http_metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUEST_TOTAL,
)
from outception.observability.utils import get_path_template


class HttpMetricsMiddleware:
    """Records metrics after the response, when scope["route"] has been set by
    FastAPI routing and the endpoint label can be the route template."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code = "500"  # kept if the app raises before responding

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path_template = get_path_template(scope)
            if path_template is not None:
                duration = time.perf_counter() - start_time
                method = scope.get("method", "UNKNOWN")

                HTTP_REQUEST_TOTAL.labels(
                    endpoint=path_template,
                    method=method,
                    status_code=status_code,
                ).inc()

                HTTP_REQUEST_DURATION_SECONDS.labels(
                    endpoint=path_template,
                    method=method,
                ).observe(duration)
