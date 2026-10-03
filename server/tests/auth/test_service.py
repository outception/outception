import pytest

from outception.auth.scope import Scope
from outception.auth.service import auth as auth_service
from outception.models import User
from outception.postgres import AsyncSession


@pytest.mark.asyncio
class TestCreateUserSession:
    async def test_creates_a_session_with_every_scope(
        self, session: AsyncSession, user: User
    ) -> None:
        token, user_session = await auth_service._create_user_session(
            session, user, user_agent="agent", scopes=list(Scope)
        )

        assert token.startswith("outception_us_")
        assert user_session.user_id == user.id
        assert set(user_session.scopes) == set(Scope)
        assert user_session.user_agent == "agent"
