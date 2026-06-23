from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import Select, or_, select, update
from sqlalchemy.orm import contains_eager

from polar.auth.models import AuthSubject
from polar.auth.scope import Scope
from polar.config import settings
from polar.email.schemas import (
    PersonalAccessTokenLeakedEmail,
    PersonalAccessTokenLeakedProps,
)
from polar.email.sender import enqueue_email_template
from polar.enums import TokenType
from polar.exceptions import PolarRequestValidationError
from polar.kit.crypto import generate_token_hash_pair, get_token_hash
from polar.kit.pagination import PaginationParams, paginate
from polar.kit.services import ResourceServiceReader
from polar.kit.utils import utc_now
from polar.logging import Logger
from polar.models import PersonalAccessToken, User
from polar.postgres import AsyncSession

from .schemas import PersonalAccessTokenCreate

log: Logger = structlog.get_logger()

TOKEN_PREFIX = "polar_pat_"


class PersonalAccessTokenService(ResourceServiceReader[PersonalAccessToken]):
    async def list(
        self,
        session: AsyncSession,
        auth_subject: AuthSubject[User],
        *,
        pagination: PaginationParams,
    ) -> tuple[Sequence[PersonalAccessToken], int]:
        statement = self._get_readable_order_statement(auth_subject)
        return await paginate(session, statement, pagination=pagination)

    async def create(
        self,
        session: AsyncSession,
        auth_subject: AuthSubject[User],
        create_schema: PersonalAccessTokenCreate,
    ) -> tuple[PersonalAccessToken, str]:
        self._validate_scopes_within_caller(auth_subject, create_schema.scopes)
        token, token_hash = generate_token_hash_pair(
            secret=settings.SECRET, prefix=TOKEN_PREFIX
        )
        personal_access_token = PersonalAccessToken(
            user=auth_subject.subject,
            token=token_hash,
            scope=" ".join(create_schema.scopes),
            comment=create_schema.comment,
            expires_at=(
                utc_now() + create_schema.expires_in
                if create_schema.expires_in
                else None
            ),
        )
        session.add(personal_access_token)
        await session.flush()
        return personal_access_token, token

    def _validate_scopes_within_caller(
        self, auth_subject: AuthSubject[User], requested_scopes: Sequence[Scope]
    ) -> None:
        # A token must never be mintable with more access than the caller holds.
        excess = set(requested_scopes) - auth_subject.scopes
        if excess:
            raise PolarRequestValidationError(
                [
                    {
                        "type": "value_error",
                        "loc": ("body", "scopes"),
                        "msg": "Requested scopes exceed the caller's own scopes.",
                        "input": sorted(s.value for s in excess),
                    }
                ]
            )

    async def get_by_id(
        self, session: AsyncSession, auth_subject: AuthSubject[User], id: UUID
    ) -> PersonalAccessToken | None:
        statement = self._get_readable_order_statement(auth_subject).where(
            PersonalAccessToken.id == id,
            PersonalAccessToken.is_deleted.is_(False),
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_token(
        self, session: AsyncSession, token: str, *, expired: bool = False
    ) -> PersonalAccessToken | None:
        token_hash = get_token_hash(token, secret=settings.SECRET)
        statement = (
            select(PersonalAccessToken)
            .join(PersonalAccessToken.user)
            .where(
                PersonalAccessToken.token == token_hash,
                PersonalAccessToken.is_deleted.is_(False),
                User.can_authenticate.is_(True),
            )
            .options(contains_eager(PersonalAccessToken.user))
        )
        if not expired:
            statement = statement.where(
                or_(
                    PersonalAccessToken.expires_at.is_(None),
                    PersonalAccessToken.expires_at > utc_now(),
                )
            )

        result = await session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def delete(
        self, session: AsyncSession, personal_access_token: PersonalAccessToken
    ) -> None:
        personal_access_token.set_deleted_at()
        session.add(personal_access_token)

    async def record_usage(
        self, session: AsyncSession, id: UUID, last_used_at: datetime
    ) -> None:
        statement = (
            update(PersonalAccessToken)
            .where(PersonalAccessToken.id == id)
            .values(last_used_at=last_used_at)
        )
        await session.execute(statement)

    async def revoke_leaked(
        self,
        session: AsyncSession,
        token: str,
        token_type: TokenType,
        *,
        notifier: str,
        url: str | None = None,
    ) -> bool:
        personal_access_token = await self.get_by_token(session, token)

        if personal_access_token is None:
            return False

        personal_access_token.set_deleted_at()
        session.add(personal_access_token)

        email = personal_access_token.user.email

        enqueue_email_template(
            PersonalAccessTokenLeakedEmail(
                props=PersonalAccessTokenLeakedProps(
                    email=email,
                    personal_access_token=personal_access_token.comment,
                    notifier=notifier,
                    url=url or "",
                )
            ),
            to_email_addr=email,
            subject="Security Notice - Your Outception Personal Access Token has been leaked",
        )

        log.info(
            "Revoke leaked personal access token",
            id=personal_access_token.id,
            notifier=notifier,
            url=url,
        )

        return True

    def _get_readable_order_statement(
        self, auth_subject: AuthSubject[User]
    ) -> Select[tuple[PersonalAccessToken]]:
        return select(PersonalAccessToken).where(
            PersonalAccessToken.user_id == auth_subject.subject.id,
            PersonalAccessToken.is_deleted.is_(False),
        )


personal_access_token = PersonalAccessTokenService(PersonalAccessToken)
