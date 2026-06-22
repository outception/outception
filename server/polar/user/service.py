from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, update

from polar.exceptions import PolarError
from polar.kit.anonymization import anonymize_email_for_deletion
from polar.models import NotificationRecipient, User
from polar.organization.repository import OrganizationRepository
from polar.postgres import AsyncSession
from polar.worker import enqueue_job

from .repository import UserRepository
from .schemas import (
    BlockingOrganization,
    UserDeletionBlockedReason,
    UserDeletionResponse,
    UserSignupAttribution,
    UserUpdate,
)

log = structlog.get_logger()


class UserError(PolarError): ...


class IdentityAlreadyVerified(UserError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        message = "Your identity is already verified."
        super().__init__(message, 403)


class IdentityVerificationProcessing(UserError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        message = "Your identity verification is still processing."
        super().__init__(message, 403)


class IdentityVerificationDoesNotExist(UserError):
    def __init__(self, identity_verification_id: str) -> None:
        self.identity_verification_id = identity_verification_id
        message = (
            f"Received identity verification {identity_verification_id} from Stripe, "
            "but no associated User exists."
        )
        super().__init__(message)


class InvalidAccount(UserError):
    def __init__(self, account_id: UUID) -> None:
        self.account_id = account_id
        message = (
            f"The account {account_id} does not exist or you don't have access to it."
        )
        super().__init__(message)


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

        return (user, created)

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

        Note: The user's Account (payout account) is not deleted here.
        Accounts are tied to organizations and should be deleted when the
        organization is deleted, not when the user account is deleted.
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
        await self._delete_notification_recipients(session, user)

        log.info("user.deleted", user_id=user.id)

        return user

    async def _delete_oauth_accounts(self, session: AsyncSession, user: User) -> None:
        """Delete all OAuth accounts for a user."""
        for account in user.oauth_accounts:
            await session.delete(account)

    async def _delete_notification_recipients(
        self,
        session: AsyncSession,
        user: User,
    ) -> None:
        """Soft-delete all notification recipients for a user."""
        stmt = (
            update(NotificationRecipient)
            .where(NotificationRecipient.user_id == user.id)
            .where(NotificationRecipient.is_deleted.is_(False))
            .values(deleted_at=func.now())
        )
        await session.execute(stmt)

        log.info(
            "user.notification_recipients_deleted",
            user_id=user.id,
        )


user = UserService()
