from typing import Any

from githubkit import (
    GitHub,
    Response,
    TokenAuthStrategy,
)


class UnexpectedStatusCode(Exception): ...


class AuthenticationRequired(UnexpectedStatusCode): ...


class Forbidden(UnexpectedStatusCode): ...


class NotFound(UnexpectedStatusCode): ...


class ValidationFailed(UnexpectedStatusCode): ...


HTTP_EXCEPTIONS = {
    401: AuthenticationRequired,
    403: Forbidden,
    404: NotFound,
    422: ValidationFailed,
}

###############################################################################
# GITHUB API HELPERS
###############################################################################


def ensure_expected_response(
    response: Response[Any], accepted: set[int] = {200, 304}
) -> bool:
    status_code = response.status_code
    if status_code in accepted:
        return True

    http_exception = HTTP_EXCEPTIONS.get(status_code, UnexpectedStatusCode)
    raise http_exception()


###############################################################################
# GITHUB API CLIENTS
###############################################################################


def get_client(access_token: str) -> GitHub[TokenAuthStrategy]:
    return GitHub(access_token, http_cache=False)


__all__ = [
    "GitHub",
    "Response",
    "TokenAuthStrategy",
    "get_client",
]
