from collections.abc import Awaitable, Callable
from inspect import Parameter, Signature
from typing import Annotated, Any

from fastapi import Depends, Request, Security
from fastapi.security import OpenIdConnect
from makefun import with_signature

from outception.auth.exceptions import SessionNotFreshError
from outception.auth.scope import Scope
from outception.config import settings
from outception.exceptions import NotPermitted, Unauthorized
from outception.kit.utils import utc_now
from outception.models import UserSession
from outception.oauth2.exceptions import InsufficientScopeError

from .models import (
    Anonymous,
    AuthSubject,
    Subject,
    SubjectType,
    User,
    is_anonymous,
    is_web_session,
)

oidc_scheme = OpenIdConnect(
    scheme_name="oidc",
    openIdConnectUrl="/.well-known/openid-configuration",
    auto_error=False,
)
_auth_subject_factory_cache: dict[
    frozenset[SubjectType], Callable[..., Awaitable[AuthSubject[Subject]]]
] = {}


def _get_auth_subject_factory(
    allowed_subjects: frozenset[SubjectType],
) -> Callable[..., Awaitable[AuthSubject[Subject]]]:
    if allowed_subjects in _auth_subject_factory_cache:
        return _auth_subject_factory_cache[allowed_subjects]

    parameters: list[Parameter] = [
        Parameter(
            name="request",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Request,
        )
    ]
    if User in allowed_subjects:
        parameters += [
            Parameter(
                name="oauth2_credentials",
                kind=Parameter.KEYWORD_ONLY,
                default=Depends(oidc_scheme),
            )
        ]

    signature = Signature(parameters)

    @with_signature(signature)
    async def get_auth_subject(request: Request, **kwargs: Any) -> AuthSubject[Subject]:
        try:
            return request.state.auth_subject
        except AttributeError as e:
            raise RuntimeError(
                "AuthSubject is not present in the request state. "
                "Did you forget to add AuthSubjectMiddleware?"
            ) from e

    _auth_subject_factory_cache[allowed_subjects] = get_auth_subject

    return get_auth_subject


class _Authenticator:
    def __init__(
        self,
        *,
        allowed_subjects: frozenset[SubjectType],
        required_scopes: set[Scope] | None = None,
    ) -> None:
        self.allowed_subjects = allowed_subjects
        self.required_scopes = required_scopes

    async def __call__(
        self, auth_subject: AuthSubject[Subject]
    ) -> AuthSubject[Subject]:
        # Not allowed subject, fallback to Anonymous
        subject_type = type(auth_subject.subject)
        if subject_type not in self.allowed_subjects:
            auth_subject = AuthSubject(Anonymous(), set(), None)

        # Anonymous
        if is_anonymous(auth_subject):
            if Anonymous in self.allowed_subjects:
                return auth_subject
            else:
                raise Unauthorized()

        # No required scopes
        if not self.required_scopes:
            return auth_subject

        # Have at least one of the required scopes. Allow this request.
        if auth_subject.scopes & self.required_scopes:
            return auth_subject

        raise InsufficientScopeError({s for s in self.required_scopes})


def Authenticator(
    allowed_subjects: set[SubjectType],
    required_scopes: set[Scope] | None = None,
) -> _Authenticator:
    """
    Here comes some blood magic 🧙‍♂️

    Generate a version of `_Authenticator` with an overriden `__call__` signature.

    By doing so, we can dynamically inject the required scopes into FastAPI
    dependency, so they are properrly detected by the OpenAPI generator.
    """
    allowed_subjects_frozen = frozenset(allowed_subjects)

    parameters: list[Parameter] = [
        Parameter(name="self", kind=Parameter.POSITIONAL_OR_KEYWORD),
        Parameter(
            name="auth_subject",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=Security(
                _get_auth_subject_factory(allowed_subjects_frozen),
                scopes=sorted(s.value for s in (required_scopes or {})),
            ),
        ),
    ]
    signature = Signature(parameters)

    class _AuthenticatorSignature(_Authenticator):
        @with_signature(signature)
        async def __call__(
            self, auth_subject: AuthSubject[Subject]
        ) -> AuthSubject[Subject]:
            return await super().__call__(auth_subject)

    return _AuthenticatorSignature(
        allowed_subjects=allowed_subjects_frozen, required_scopes=required_scopes
    )


_WebUserOrAnonymous = Authenticator(
    allowed_subjects={Anonymous, User},
    required_scopes=None,
)


async def _web_user_or_anonymous(
    auth_subject: Annotated[
        AuthSubject[Anonymous | User], Depends(_WebUserOrAnonymous)
    ],
) -> AuthSubject[Anonymous | User]:
    """Allow anonymous or web-session users. Reject API tokens."""
    if not is_anonymous(auth_subject) and not is_web_session(auth_subject):
        raise NotPermitted()
    return auth_subject


WebUserOrAnonymous = Annotated[
    AuthSubject[Anonymous | User], Depends(_web_user_or_anonymous)
]

_WebUserAuth = Authenticator(allowed_subjects={User}, required_scopes=None)


async def _web_user(
    auth_subject: Annotated[AuthSubject[User], Depends(_WebUserAuth)],
) -> AuthSubject[User]:
    """Allow web-session users only. Reject API tokens."""
    if not is_web_session(auth_subject):
        raise NotPermitted()
    return auth_subject


WebUserSession = Annotated[AuthSubject[User], Depends(_web_user)]


# ---------------------------------------------------------------------------
# Scoped authorizers.
#
# ``WebUser{Read,Write,WriteFresh}``: a User via web session only; API tokens
# are rejected. ``User{Read,Write}``: any User subject (web session or OAuth2
# access token) with the matching scope, for endpoints the app calls with a
# token. Read aliases accept the read or the write scope; write aliases
# require the write scope.
# ---------------------------------------------------------------------------


def WebUserAuthorizer(required_scopes: set[Scope]) -> Any:
    async def dependency(auth_subject: WebUserSession) -> AuthSubject[User]:
        if not (auth_subject.scopes & required_scopes):
            raise InsufficientScopeError({s.value for s in required_scopes})
        return auth_subject

    return dependency


def ensure_session_fresh(auth_subject: AuthSubject[User]) -> None:
    """Require a recently authenticated web session for sensitive operations.

    Logging in always creates a new ``UserSession``, so ``created_at`` is the
    time of the last authentication.
    """
    if not isinstance(auth_subject.session, UserSession):
        raise NotPermitted()
    if (
        utc_now() - auth_subject.session.created_at
        > settings.USER_SESSION_FRESHNESS_TTL
    ):
        raise SessionNotFreshError()


def WebUserAuthorizerFresh(required_scopes: set[Scope]) -> Any:
    async def dependency(
        auth_subject: Annotated[
            AuthSubject[User], Depends(WebUserAuthorizer(required_scopes))
        ],
    ) -> AuthSubject[User]:
        ensure_session_fresh(auth_subject)
        return auth_subject

    return dependency


WebUserRead = Annotated[
    AuthSubject[User],
    Depends(WebUserAuthorizer({Scope.user_read, Scope.user_write})),
]
WebUserWrite = Annotated[
    AuthSubject[User],
    Depends(WebUserAuthorizer({Scope.user_write})),
]
WebUserWriteFresh = Annotated[
    AuthSubject[User],
    Depends(WebUserAuthorizerFresh({Scope.user_write})),
]

_UserRead = Authenticator(
    allowed_subjects={User}, required_scopes={Scope.user_read, Scope.user_write}
)
_UserWrite = Authenticator(allowed_subjects={User}, required_scopes={Scope.user_write})
UserRead = Annotated[AuthSubject[User], Depends(_UserRead)]
UserWrite = Annotated[AuthSubject[User], Depends(_UserWrite)]
