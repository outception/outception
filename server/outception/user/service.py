from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError

from outception.exceptions import OutceptionError
from outception.kit.anonymization import anonymize_email_for_deletion
from outception.models import User
from outception.postgres import AsyncSession

from .repository import UserRepository
from .schemas import UserDeletionResponse, UserSignupAttribution, UserUpdate

log = structlog.get_logger()


class UserError(OutceptionError): ...


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
        if user is not None:
            return (user, False)

        try:
            async with session.begin_nested():
                user = await self.create_by_email(
                    session, email, signup_attribution=signup_attribution
                )
        except IntegrityError:
            user = await repository.get_by_email(email)
            if user is None:
                raise
            log.info("user.get_by_email_or_create.concurrent_creation", user_id=user.id)
            return (user, False)

        return (user, True)

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
        log.info("user.signup", user_id=user.id)
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

        if (
            update_dict.pop("accepted_terms_of_service", None) is True
            and not user.accepted_terms_of_service
        ):
            update_dict["accepted_terms_of_service_at"] = datetime.now(UTC)
            update_dict["accepted_terms_of_service_ip"] = ip_address

        repository = UserRepository.from_session(session)
        return await repository.update(user, update_dict=update_dict)

    async def request_deletion(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserDeletionResponse:
        """Delete the user account. Nothing blocks it: a reader owns no shared
        resource that has to be handed over first."""
        await self.soft_delete_user(session, user)
        return UserDeletionResponse(deleted=True)

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
