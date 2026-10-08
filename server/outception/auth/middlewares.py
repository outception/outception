import logfire
import structlog
from fastapi import Request
from fastapi.security.utils import get_authorization_scheme_param
from starlette.types import ASGIApp, Receive, Send
from starlette.types import Scope as ASGIScope

from outception.config import settings
from outception.exception_handlers import outception_exception_handler
from outception.logging import Logger
from outception.models import OAuth2Token, User, UserSession
from outception.oauth2.constants import (
    is_access_token_prefix,
    is_registration_token_prefix,
)
from outception.oauth2.exception_handlers import (
    OAuth2Error,
    oauth2_error_exception_handler,
)
from outception.oauth2.exceptions import InvalidTokenError
from outception.oauth2.service.oauth2_token import oauth2_token as oauth2_token_service
from outception.postgres import AsyncSession
from outception.rate_limit import clear_cached_identity, write_cached_identity
from outception.redis import Redis
from outception.sentry import set_sentry_user

from .exceptions import OutceptionAuthError
from .models import Anonymous, AuthSubject, Subject
from .service import auth as auth_service

log: Logger = structlog.get_logger(__name__)


async def get_user_session(
    request: Request, session: AsyncSession
) -> UserSession | None:
    return await auth_service.authenticate(session, request)


def get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    scheme, value = get_authorization_scheme_param(authorization)
    if not scheme or not value or scheme.lower() != "bearer":
        return None
    if not value.isascii():
        return None
    return value


async def get_oauth2_token(session: AsyncSession, value: str) -> OAuth2Token | None:
    return await oauth2_token_service.get_by_access_token(session, value)


async def get_auth_subject(
    request: Request, session: AsyncSession
) -> AuthSubject[Subject]:
    subject: User
    credential: UserSession | OAuth2Token
    token = get_bearer_token(request)
    if token is not None and is_registration_token_prefix(token):
        return AuthSubject(Anonymous(), set(), None)

    if token is not None and is_access_token_prefix(token):
        oauth2_token = await get_oauth2_token(session, token)
        if oauth2_token is None:
            raise InvalidTokenError()
        subject = oauth2_token.sub
        scopes = oauth2_token.scopes
        credential = oauth2_token
    elif token is not None:
        raise InvalidTokenError()
    else:
        user_session = await get_user_session(request, session)
        if user_session is None:
            return AuthSubject(Anonymous(), set(), None)
        subject = user_session.user
        scopes = set(user_session.scopes)
        credential = user_session

    return AuthSubject(subject, scopes, credential)


class AuthSubjectMiddleware:
    def __init__(self, app: ASGIApp, redis: Redis) -> None:
        self.app = app
        self.redis = redis

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        session: AsyncSession = scope["state"]["async_session"]
        request = Request(scope)

        try:
            auth_subject = await get_auth_subject(request, session)
        except OAuth2Error as e:
            token = get_bearer_token(request)
            if token is not None:
                await clear_cached_identity(self.redis, token)
            response = await oauth2_error_exception_handler(request, e)
            request.state.transaction_failed = True
            return await response(scope, receive, send)
        except OutceptionAuthError as e:
            response = await outception_exception_handler(request, e)
            request.state.transaction_failed = True
            return await response(scope, receive, send)

        scope["state"]["auth_subject"] = auth_subject

        cookie = request.cookies.get(settings.USER_SESSION_COOKIE_KEY)
        if not isinstance(auth_subject.subject, Anonymous):
            token = get_bearer_token(request)
            if token is not None:
                await write_cached_identity(
                    self.redis, token, auth_subject.rate_limit_key
                )
            if cookie is not None:
                await write_cached_identity(
                    self.redis, cookie, auth_subject.rate_limit_key
                )
        elif cookie is not None:
            await clear_cached_identity(self.redis, cookie)

        with logfire.set_baggage(**auth_subject.log_context):
            log.info("Authenticated subject", **auth_subject.log_context)
            set_sentry_user(auth_subject)
            # Other scope types (lifespan, etc.)
            await self.app(scope, receive, send)
