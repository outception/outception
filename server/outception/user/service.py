import secrets
from datetime import UTC, datetime
from typing import Any

import structlog
from slugify import slugify
from sqlalchemy import select, text

from outception.kit.anonymization import anonymize_email_for_deletion
from outception.models import Organization, User, UserOrganization
from outception.models.user_organization import OrganizationRole
from outception.organization.repository import OrganizationRepository
from outception.postgres import AsyncSession
from outception.worker import enqueue_job

from .repository import UserRepository
from .schemas import (
    BlockingOrganization,
    UserDeletionBlockedReason,
    UserDeletionResponse,
    UserSignupAttribution,
    UserUpdate,
)

log = structlog.get_logger()


class UserService:
    async def get_by_email_or_create(
        self,
        session: AsyncSession,
        email: str,
        *,
        signup_attribution: UserSignupAttribution | None = None,
    ) -> tuple[User, bool]:
        repository = UserRepository.from_session(session)
        user = await repository.get_by_email(email)
        created = False
        if user is None:
            user = await self.create_by_email(
                session, email, signup_attribution=signup_attribution
            )
            created = True

        # The dashboard is organization-scoped, so every user needs at least one
        # organization they own. There is no separate onboarding step —
        # provision a personal organization on first login
        # (and back-fill anyone created before this existed).
        await self.ensure_personal_organization(session, user)

        return (user, created)

    async def ensure_personal_organization(
        self, session: AsyncSession, user: User
    ) -> None:
        # Serialize concurrent logins for the same user (e.g. a double-fired
        # /complete or two tabs): without this, both transactions see "no
        # membership", derive the same email-based slug, and one 500s on the
        # unique-slug constraint. A transaction-scoped advisory lock makes the
        # check-then-create atomic per user.
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"personal-org:{user.id}"},
        )

        membership = (
            await session.execute(
                select(UserOrganization.organization_id)
                .where(
                    UserOrganization.user_id == user.id,
                    UserOrganization.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).first()
        if membership is not None:
            return

        org_repository = OrganizationRepository.from_session(session)
        local_part = user.email.split("@", 1)[0]
        base_slug = slugify(local_part) or "workspace"
        slug = base_slug
        while (
            await session.execute(
                select(Organization.id).where(Organization.slug == slug).limit(1)
            )
        ).first() is not None:
            slug = f"{base_slug}-{secrets.token_hex(3)}"

        organization = await org_repository.create(
            Organization(name=local_part or "Personal", slug=slug), flush=True
        )
        session.add(
            UserOrganization(
                user_id=user.id,
                organization_id=organization.id,
                role=OrganizationRole.owner,
            )
        )
        await session.flush()

    async def create_by_email(
        self,
        session: AsyncSession,
        email: str,
        signup_attribution: UserSignupAttribution | None = None,
    ) -> User:
        repository = UserRepository.from_session(session)
        user = await repository.create(
            User(
                email=email,
                oauth_accounts=[],
                signup_attribution=signup_attribution,
            ),
            flush=True,
        )
        enqueue_job("user.on_after_signup", user_id=user.id)
        return user

    async def update(
        self,
        session: AsyncSession,
        user: User,
        update_schema: UserUpdate,
        *,
        ip_address: str | None = None,
    ) -> User:
        update_dict = update_schema.model_dump(exclude_unset=True)

        if update_dict.pop("accepted_terms_of_service", None) is True:
            if not user.accepted_terms_of_service:
                update_dict["accepted_terms_of_service_at"] = datetime.now(UTC)
                update_dict["accepted_terms_of_service_ip"] = ip_address

        repository = UserRepository.from_session(session)
        updated_user = await repository.update(user, update_dict=update_dict)

        return updated_user

    async def check_can_delete(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserDeletionResponse:
        """Check if a user can be deleted.

        A user can be deleted if all organizations they are members of
        are soft-deleted (deleted_at is not None).
        """
        blocked_reasons: list[UserDeletionBlockedReason] = []
        blocking_organizations: list[BlockingOrganization] = []

        # Get all organizations the user is a member of (excluding deleted orgs)
        org_repository = OrganizationRepository.from_session(session)
        organizations = await org_repository.get_all_by_user(user.id)

        if organizations:
            blocked_reasons.append(UserDeletionBlockedReason.HAS_ACTIVE_ORGANIZATIONS)
            for org in organizations:
                blocking_organizations.append(
                    BlockingOrganization(id=org.id, slug=org.slug, name=org.name)
                )

        return UserDeletionResponse(
            deleted=False,
            blocked_reasons=blocked_reasons,
            blocking_organizations=blocking_organizations,
        )

    async def request_deletion(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserDeletionResponse:
        """Request deletion of the user account.

        Flow:
        1. Check if user has any active organizations -> block if yes
        2. Soft delete the user
        """
        check_result = await self.check_can_delete(session, user)

        if check_result.blocked_reasons:
            return check_result

        # Soft delete the user
        await self.soft_delete_user(session, user)

        return UserDeletionResponse(
            deleted=True,
            blocked_reasons=[],
            blocking_organizations=[],
        )

    async def soft_delete_user(
        self,
        session: AsyncSession,
        user: User,
    ) -> User:
        """Soft-delete a user, anonymizing PII fields."""
        repository = UserRepository.from_session(session)

        update_dict: dict[str, Any] = {}

        update_dict["email"] = anonymize_email_for_deletion(user.email, user.created_at)

        if user.avatar_url:
            update_dict["avatar_url"] = None

        if user.meta:
            update_dict["meta"] = {}

        user = await repository.update(user, update_dict=update_dict)
        await repository.soft_delete(user)

        await self._delete_oauth_accounts(session, user)

        log.info("user.deleted", user_id=user.id)

        return user

    async def _delete_oauth_accounts(self, session: AsyncSession, user: User) -> None:
        """Delete all OAuth accounts for a user."""
        for account in user.oauth_accounts:
            await session.delete(account)


user = UserService()
