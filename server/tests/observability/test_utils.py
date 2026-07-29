from unittest.mock import MagicMock

from outception.observability.http_metrics import (
    METRICS_EXCLUDED_APPS,
    exclude_app_from_metrics,
)
from outception.observability.utils import get_path_template


class TestGetPathTemplate:
    def test_middleware_denies_healthz(self) -> None:
        scope = {"path": "/healthz", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_uses_route_path(self) -> None:
        mock_route = MagicMock()
        mock_route.path = "/v1/checkouts/{id}"

        scope = {
            "path": "/v1/checkouts/550e8400-e29b-41d4-a716-446655440000",
            "route": mock_route,
            "type": "http",
        }

        result = get_path_template(scope)
        assert result == "/v1/checkouts/{id}"

    def test_middleware_route_without_path_attr(self) -> None:
        mock_route = MagicMock(spec=[])  # no path attribute

        scope = {
            "path": "/v1/orders/12345",
            "route": mock_route,
            "type": "http",
        }

        result = get_path_template(scope)
        assert result is None

    def test_middleware_prefix_deny(self) -> None:
        scope = {"path": "/healthz/deep", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_denies_readyz(self) -> None:
        scope = {"path": "/readyz", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_denies_well_known(self) -> None:
        scope = {"path": "/.well-known/jwks.json", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_empty_path(self) -> None:
        scope = {"path": "", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_missing_path(self) -> None:
        scope = {"type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_unknown_route_returns_none(self) -> None:
        scope = {"path": "/v1/unknown", "type": "http"}
        result = get_path_template(scope)
        assert result is None

    def test_middleware_excludes_app(self) -> None:
        mock_app = MagicMock()
        mock_route = MagicMock()
        mock_route.path = "/some/path"

        scope = {
            "path": "/some/path",
            "type": "http",
            "app": mock_app,
            "route": mock_route,
        }
        result = get_path_template(scope)
        assert result == "/some/path"

        exclude_app_from_metrics(mock_app)
        try:
            assert get_path_template(scope) is None
        finally:
            METRICS_EXCLUDED_APPS.discard(mock_app)
