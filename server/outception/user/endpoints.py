from fastapi import Depends, Request

from outception.auth.dependencies import Authenticator
from outception.auth.models import AuthSubject
from outception.authz.dependencies import (
    AuthorizeUserWrite,
    AuthorizeWebUserRead,
    AuthorizeWebUserWrite,
)
from outception.models import User
from outception.models.user import OAuthPlatform
from outception.openapi import APITag
from outception.organization.schemas import OrganizationWithRole
from outception.postgres import (
    AsyncReadSession,
    AsyncSession,
    get_db_read_session,
    get_db_session,
)
from outception.routing import APIRouter
from outception.user.oauth_service import oauth_account_service
from outception.user.service import user as user_service
from outception.user_organization.repository import UserOrganizationRepository

from .schemas import (
    UserDeletionResponse,
    UserRead,
    UserScopes,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users", APITag.private])


@router.get("/me", response_model=UserRead)
async def get_authenticated(
    auth_subject: AuthorizeWebUserRead,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> UserRead:
    user = auth_subject.subject
    repository = UserOrganizationRepository.from_session(session)
    org_with_roles = await repository.get_organizations_with_role(user.id)
    return UserRead.model_validate(user).model_copy(
        update={
            "organizations": [
                OrganizationWithRole.from_organization(org, role)
                for org, role in org_with_roles
            ]
        }
    )


@router.patch("/me", response_model=UserRead)
async def update_authenticated(
    user_update: UserUpdate,
    request: Request,
    auth_subject: AuthorizeWebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    ip_address = request.client.host if request.client else None
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
    responses={
        200: {"description": "Deletion result"},
    },
)
async def delete_authenticated_user(
    auth_subject: AuthorizeUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> UserDeletionResponse:
    """
    Delete the authenticated user account.

    A user can only be deleted if all organizations they are members of have been
    deleted first. If the user has active organizations, the response will include
    the list of organizations that must be deleted before the user account can be
    removed.

    When deleted:
    - User's email is anonymized
    - User's avatar and metadata are cleared
    - User's OAuth accounts are deleted (cascade)
    - User's Account (payout account) is deleted if present
    """
    return await user_service.request_deletion(session, auth_subject.subject)


@router.delete(
    "/me/oauth-accounts/{platform}",
    status_code=204,
    responses={
        404: {"description": "OAuth account not found"},
        400: {"description": "Cannot disconnect last authentication method"},
    },
)
async def disconnect_oauth_account(
    platform: OAuthPlatform,
    auth_subject: AuthorizeWebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Disconnect an OAuth account (GitHub or Google) from the authenticated user.

    This allows users to unlink their OAuth provider while keeping their Outception account.
    They can still authenticate using other methods (email magic link or other OAuth providers).

    Note: You cannot disconnect your last authentication method if your email is not verified.
    """
    user = auth_subject.subject
    await oauth_account_service.disconnect_platform(session, user, platform)
