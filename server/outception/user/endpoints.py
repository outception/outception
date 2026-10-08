from fastapi import Depends, Request

from outception.auth.dependencies import (
    Authenticator,
    UserWrite,
    WebUserRead,
    WebUserWrite,
    WebUserWriteFresh,
)
from outception.auth.exceptions import SessionNotFreshError
from outception.auth.models import AuthSubject
from outception.kit.http import get_ip_address
from outception.models import User
from outception.models.user import OAuthPlatform
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.routing import APIRouter
from outception.user.oauth_service import oauth_account_service
from outception.user.service import user as user_service

from .schemas import UserDeletionResponse, UserRead, UserScopes, UserUpdate

router = APIRouter(prefix="/users", tags=["users", APITag.private])


@router.get("/me", response_model=UserRead)
async def get_authenticated(auth_subject: WebUserRead) -> User:
    return auth_subject.subject


@router.patch("/me", response_model=UserRead)
async def update_authenticated(
    user_update: UserUpdate,
    request: Request,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    ip_address = get_ip_address(request)
    return await user_service.update(
        session, auth_subject.subject, user_update, ip_address=ip_address
    )


@router.get("/me/scopes", response_model=UserScopes)
async def scopes(
    auth_subject: AuthSubject[User] = Depends(Authenticator(allowed_subjects={User})),
) -> UserScopes:
    return UserScopes(scopes=list(auth_subject.scopes))


@router.delete(
    "/me",
    response_model=UserDeletionResponse,
    responses={200: {"description": "Deletion result"}},
)
async def delete_authenticated_user(
    auth_subject: UserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> UserDeletionResponse:
    """Delete the authenticated user account: the email is anonymized, the
    avatar and metadata are cleared, social accounts, sessions, follows and
    preferences go with it."""
    return await user_service.request_deletion(session, auth_subject.subject)


@router.delete(
    "/me/oauth-accounts/{platform}",
    status_code=204,
    responses={
        404: {"description": "Social account not found"},
        400: {"description": "Cannot disconnect last authentication method"},
        403: {"model": SessionNotFreshError.schema()},
    },
)
async def disconnect_oauth_account(
    platform: OAuthPlatform,
    auth_subject: WebUserWriteFresh,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Disconnect a social login from the authenticated user. The account
    stays; the other login methods keep working. The last method cannot be
    disconnected while the email is unverified."""
    user = auth_subject.subject
    await oauth_account_service.disconnect_platform(session, user, platform)
