import pytest

from outception.models import User
from outception.postgres import AsyncSession
from outception.user.repository import UserRepository
from outception.user.schemas import UserUpdate
from outception.user.service import user as user_service
from tests.fixtures.database import SaveFixture
from tests.fixtures.random_objects import create_user_google_oauth


@pytest.mark.asyncio
class TestGetByEmailOrCreate:
    async def test_existing(self, session: AsyncSession, user: User) -> None:
        found, created = await user_service.get_by_email_or_create(
            session, user.email.upper()
        )

        assert found.id == user.id
        assert created is False

    async def test_new(self, session: AsyncSession) -> None:
        found, created = await user_service.get_by_email_or_create(
            session, "new@example.com"
        )

        assert created is True
        assert found.email == "new@example.com"
        assert found.email_verified is False


@pytest.mark.asyncio
class TestUpdate:
    async def test_accepts_terms_once(self, session: AsyncSession, user: User) -> None:
        updated = await user_service.update(
            session,
            user,
            UserUpdate(accepted_terms_of_service=True),
            ip_address="203.0.113.7",
        )

        assert updated.accepted_terms_of_service is True
        assert updated.accepted_terms_of_service_ip == "203.0.113.7"
        first = updated.accepted_terms_of_service_at

        updated = await user_service.update(
            session, updated, UserUpdate(accepted_terms_of_service=True)
        )

        assert updated.accepted_terms_of_service_at == first


@pytest.mark.asyncio
class TestRequestDeletion:
    async def test_deletes_and_anonymizes(
        self, session: AsyncSession, save_fixture: SaveFixture, user: User
    ) -> None:
        await create_user_google_oauth(save_fixture, user)
        original_email = user.email

        result = await user_service.request_deletion(session, user)

        assert result.deleted is True
        assert user.deleted_at is not None
        assert user.email != original_email
        assert user.avatar_url is None

        repository = UserRepository.from_session(session)
        assert await repository.get_by_email(original_email) is None
