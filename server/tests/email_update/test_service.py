from datetime import timedelta

import pytest

from outception.auth.models import AuthSubject
from outception.email_update.service import InvalidEmailUpdate
from outception.email_update.service import email_update as email_update_service
from outception.exceptions import OutceptionRequestValidationError
from outception.kit.utils import utc_now
from outception.models import User
from outception.postgres import AsyncSession


def _auth(user: User) -> AuthSubject[User]:
    return AuthSubject(user, set(), None)


@pytest.mark.asyncio
class TestRequestEmailUpdate:
    async def test_rejects_email_used_by_another_user(
        self, session: AsyncSession, user: User, user_second: User
    ) -> None:
        with pytest.raises(OutceptionRequestValidationError):
            await email_update_service.request_email_update(
                user_second.email, session, _auth(user)
            )

    async def test_allows_new_unused_email(
        self, session: AsyncSession, user: User
    ) -> None:
        record, token = await email_update_service.request_email_update(
            "brand-new@example.com", session, _auth(user)
        )
        assert record.email == "brand-new@example.com"
        assert record.user_id == user.id
        assert token


@pytest.mark.asyncio
class TestVerify:
    async def test_changes_email_and_is_single_use(
        self, session: AsyncSession, user: User
    ) -> None:
        _, token = await email_update_service.request_email_update(
            "changed@example.com", session, _auth(user)
        )
        updated = await email_update_service.verify(session, token, user)
        assert updated.email == "changed@example.com"

        # The token is consumed — a replay must fail.
        with pytest.raises(InvalidEmailUpdate):
            await email_update_service.verify(session, token, user)

    async def test_rejects_another_users_token(
        self, session: AsyncSession, user: User, user_second: User
    ) -> None:
        _, token = await email_update_service.request_email_update(
            "wanted@example.com", session, _auth(user)
        )
        # user_second must not be able to redeem a token issued to user.
        with pytest.raises(InvalidEmailUpdate):
            await email_update_service.verify(session, token, user_second)

    async def test_rejects_expired_token(
        self, session: AsyncSession, user: User
    ) -> None:
        record, token = await email_update_service.request_email_update(
            "late@example.com", session, _auth(user)
        )
        record.expires_at = utc_now() - timedelta(seconds=1)
        session.add(record)
        await session.flush()

        with pytest.raises(InvalidEmailUpdate):
            await email_update_service.verify(session, token, user)

    async def test_rejects_unknown_token(
        self, session: AsyncSession, user: User
    ) -> None:
        with pytest.raises(InvalidEmailUpdate):
            await email_update_service.verify(session, "outception_ev_nonsense", user)
