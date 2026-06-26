from outception.auth.models import AuthSubject, Organization, User
from outception.auth.permission import OrganizationPermission
from outception.authz.types import PolicyResult
from outception.models import Organization as OrganizationModel
from outception.postgres import AsyncReadSession

from . import _require_permission


async def can_manage(
    session: AsyncReadSession,
    auth_subject: AuthSubject[User | Organization],
    organization: OrganizationModel,
) -> PolicyResult:
    """Can the subject edit, delete, or set the payout account for this organization?"""
    return await _require_permission(
        session,
        auth_subject,
        organization,
        permission=OrganizationPermission.organization_manage,
    )
