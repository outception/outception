from typing import Protocol

from pydantic import UUID4

from outception.auth.models import AuthSubject, is_organization
from outception.authz.service import get_accessible_org_ids
from outception.exceptions import OutceptionRequestValidationError
from outception.models import Organization, User
from outception.organization.repository import OrganizationRepository
from outception.postgres import AsyncSession


class _OrganizationIDModelNone(Protocol):
    organization_id: UUID4 | None


class _OrganizationIDModel(Protocol):
    organization_id: UUID4


OrganizationIDModel = _OrganizationIDModelNone | _OrganizationIDModel


async def get_payload_organization(
    session: AsyncSession,
    auth_subject: AuthSubject[User | Organization],
    model: OrganizationIDModel,
) -> Organization:
    if is_organization(auth_subject):
        if model.organization_id is not None:
            raise OutceptionRequestValidationError(
                [
                    {
                        "type": "organization_token",
                        "msg": (
                            "Setting organization_id is disallowed "
                            "when using an organization token."
                        ),
                        "loc": (
                            "body",
                            "organization_id",
                        ),
                        "input": model.organization_id,
                    }
                ]
            )
        return auth_subject.subject

    if model.organization_id is None:
        raise OutceptionRequestValidationError(
            [
                {
                    "type": "missing",
                    "msg": "organization_id is required.",
                    "loc": (
                        "body",
                        "organization_id",
                    ),
                    "input": None,
                }
            ]
        )

    accessible = await get_accessible_org_ids(session, auth_subject)
    if model.organization_id not in accessible:
        raise OutceptionRequestValidationError(
            [
                {
                    "loc": (
                        "body",
                        "organization_id",
                    ),
                    "msg": "Organization not found.",
                    "type": "value_error",
                    "input": model.organization_id,
                }
            ]
        )

    repository = OrganizationRepository.from_session(session)
    organization = await repository.get_by_id(model.organization_id)

    if organization is None:
        raise OutceptionRequestValidationError(
            [
                {
                    "loc": (
                        "body",
                        "organization_id",
                    ),
                    "msg": "Organization not found.",
                    "type": "value_error",
                    "input": model.organization_id,
                }
            ]
        )

    return organization
