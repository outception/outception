from starlette.types import Scope

from .http_metrics import METRICS_DENY_LIST, METRICS_EXCLUDED_APPS


def get_path_template(scope: Scope) -> str | None:
    """Return the route template to label metrics with, or None to skip.

    None for deny-listed paths, excluded apps, and requests that matched no
    route: labelling raw 404 paths would let scanners blow up cardinality.
    """
    app = scope.get("app")
    if app is not None and app in METRICS_EXCLUDED_APPS:
        return None

    path = scope.get("path", "")
    if path in METRICS_DENY_LIST:
        return None
    for denied in METRICS_DENY_LIST:
        if path.startswith(denied):
            return None

    route = scope.get("route")
    if route and hasattr(route, "path"):
        # Starlette 1.x includes routers as objects without `path`; only
        # concrete routes carry a template.
        template = getattr(route, "path", None)
        if isinstance(template, str):
            return template
    return None
