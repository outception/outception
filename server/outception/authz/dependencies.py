from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends

from outception.auth.dependencies import Authenticator, WebUserSession
from outception.auth.models import AuthSubject, Organization, User
from outception.auth.scope import Scope
from outception.exceptions import NotPermitted, ResourceNotFound
from outception.models import Organization as OrganizationModel
from outception.oauth2.exceptions import InsufficientScopeError
from outception.organization.schemas import OrganizationID
from outception.postgres import AsyncSession, get_db_session

from .policies import members
from .policies import organization as org_policy
from .service import get_accessible_organization
from .types import PolicyFn


@dataclass(frozen=True)
class AuthzContext[S: User | Organization]:
    """Result of an OrgPolicyGuard dependency.

    Contains both the resolved organization and the authenticated subject,
    so endpoints have a single entry point for auth context.

    The type parameter ``S`` reflects which subject types the guard allows,
    giving endpoints automatic type narrowing without ``assert is_user()``.
    """

    organization: OrganizationModel
    auth_subject: AuthSubject[S]


def OrgPolicyGuard(
    policy_fn: PolicyFn | None = None,
    *,
    allowed_subjects: set[type] | None = None,
    required_scopes: set[Scope] | None = None,
) -> Any:
    """Create a FastAPI dependency that authenticates, resolves an organization,
    and (optionally) checks a policy.

    Steps:
    1. Authenticate the subject via Authenticator.
    2. Resolve the organization from the ``{id}`` path parameter.
    3. Verify the subject is a member of the organization.
    4. Evaluate the policy function if provided.
    5. Return an ``AuthzContext`` (organization + auth_subject).

    Raises:
        Unauthorized (401): The request has no valid credentials, or the
            subject type is not in ``allowed_subjects``.
        InsufficientScopeError (403): The token lacks the required scopes.
        ResourceNotFound (404): The organization does not exist, or the
            subject is not a member of it. Both cases return 404 to avoid
            leaking the existence of organizations the subject cannot access.
        NotPermitted (403): The policy function denied access (e.g. the
            subject is a member but lacks `finance:read` for finance endpoints).
    """

    _allowed = allowed_subjects or {User, Organization}
    _scopes = required_scopes or {
        Scope.organizations_read,
        Scope.organizations_write,
    }

    _authenticator = Authenticator(
        allowed_subjects=_allowed,
        required_scopes=_scopes,
    )

    async def dependency(
        id: OrganizationID,
        auth_subject: Annotated[
            AuthSubject[User | Organization], Depends(_authenticator)
        ],
        session: AsyncSession = Depends(get_db_session),
    ) -> AuthzContext[User | Organization]:
        organization = await get_accessible_organization(session, auth_subject, id)
        if organization is None:
            raise ResourceNotFound()

        if policy_fn is not None:
            result = await policy_fn(session, auth_subject, organization)
            if result is not True:
                raise NotPermitted(result)
        return AuthzContext(organization=organization, auth_subject=auth_subject)

    return dependency


AuthorizeMembersRead = Annotated[
    AuthzContext[User | Organization],
    Depends(
        OrgPolicyGuard(
            members.can_read,
            required_scopes={
                Scope.organizations_read,
                Scope.organizations_write,
            },
        )
    ),
]
# Both `AuthorizeMembersManage` and `AuthorizeMembersSetRole` enforce the
# same `members:manage` policy; they differ only by the OAuth scope they
# accept. `members:manage` covers invite/remove (general member admin);
# `members:set_role` is a separate scope for the narrower role-change
# action so callers can opt into the lesser privilege.
AuthorizeMembersManage = Annotated[
    AuthzContext[User],
    Depends(
        OrgPolicyGuard(
            members.can_manage,
            allowed_subjects={User},
            required_scopes={Scope.organizations_write},
        )
    ),
]
AuthorizeMembersSetRole = Annotated[
    AuthzContext[User],
    Depends(
        OrgPolicyGuard(
            members.can_manage,
            allowed_subjects={User},
            required_scopes={Scope.members_write},
        )
    ),
]
AuthorizeOrgManage = Annotated[
    AuthzContext[User | Organization],
    Depends(
        OrgPolicyGuard(
            org_policy.can_manage,
            required_scopes={Scope.organizations_write},
        )
    ),
]
# Read-only counterpart to `AuthorizeOrgManage`: same `can_manage` policy
# (so the endpoint is still gated to org admins) but accepts either the
# read or write scope, so read-only sessions (e.g. backoffice impersonation)
# can hit GET endpoints that expose admin-only data.
AuthorizeOrgManageRead = Annotated[
    AuthzContext[User | Organization],
    Depends(
        OrgPolicyGuard(
            org_policy.can_manage,
            required_scopes={
                Scope.organizations_read,
                Scope.organizations_write,
            },
        )
    ),
]
AuthorizeOrgManageUser = Annotated[
    AuthzContext[User],
    Depends(
        OrgPolicyGuard(
            org_policy.can_manage,
            allowed_subjects={User},
            required_scopes={Scope.organizations_write},
        )
    ),
]
AuthorizeOrgAccess = Annotated[
    AuthzContext[User | Organization], Depends(OrgPolicyGuard())
]
AuthorizeOrgAccessUser = Annotated[
    AuthzContext[User],
    Depends(
        OrgPolicyGuard(
            allowed_subjects={User},
            required_scopes={Scope.organizations_write},
        )
    ),
]


# ---------------------------------------------------------------------------
# User-personal authorization
# ---------------------------------------------------------------------------
# For endpoints that operate on the authenticated user themselves (own
# profile, own PATs, OAuth identity links, email update, etc.) — i.e. no
# organization resource to authorize against. The user-personal analogue of
# OrgPolicyGuard.
#
# Two prefixes:
#
# - ``AuthorizeWeb{User,Payouts}{Read,Write}`` — User **via web session**
#   only. Rejects API tokens (PATs, OATs, OAuth2 access tokens). Use for
#   browser/dashboard-only flows.
# - ``Authorize{User}{Read,Write}`` — Any User subject (web session, PAT,
#   OAuth2 access token) with the appropriate scope. Use for endpoints that
#   legitimately accept API tokens (e.g. mobile app account deletion).
#
# Read aliases accept either the matching ``_read`` or ``_write`` scope
# (write implies read). Write aliases require the ``_write`` scope. This
# scope check is the read/write gate for impersonation: impersonation
# sessions only carry ``READ_ONLY_SCOPES``, so they are rejected from any
# endpoint requiring a ``_write`` scope — regardless of which prefix is used.
# ---------------------------------------------------------------------------


def WebUserAuthorizer(required_scopes: set[Scope]) -> Any:
    """FastAPI dependency: authenticate as a User **via web session** (via
    ``WebUserSession``, which rejects API tokens) and require at least one
    of the given scopes."""

    async def dependency(
        auth_subject: WebUserSession,
    ) -> AuthSubject[User]:
        if not (auth_subject.scopes & required_scopes):
            raise InsufficientScopeError({s.value for s in required_scopes})
        return auth_subject

    return dependency


AuthorizeWebUserRead = Annotated[
    AuthSubject[User],
    Depends(WebUserAuthorizer({Scope.user_read, Scope.user_write})),
]
AuthorizeWebUserWrite = Annotated[
    AuthSubject[User],
    Depends(WebUserAuthorizer({Scope.user_write})),
]


# ``Authorize{User}{Read,Write}`` — any User subject (web, PAT, OAuth2) +
# scope check. Use these only for endpoints that need to accept API tokens.
AuthorizeUserRead = Annotated[
    AuthSubject[User],
    Depends(
        Authenticator(
            allowed_subjects={User},
            required_scopes={Scope.user_read, Scope.user_write},
        )
    ),
]
AuthorizeUserWrite = Annotated[
    AuthSubject[User],
    Depends(
        Authenticator(
            allowed_subjects={User},
            required_scopes={Scope.user_write},
        )
    ),
]
