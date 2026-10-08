import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.models import User


@pytest.mark.asyncio
class TestAdminFlag:
    @pytest.mark.auth
    async def test_listed_address_reads_as_admin(
        self, client: AsyncClient, user: User, mocker: MockerFixture
    ) -> None:
        assert (await client.get("/v1/users/me")).json()["is_admin"] is False
        mocker.patch.object(settings, "ADMIN_EMAILS", [user.email.upper()])
        assert (await client.get("/v1/users/me")).json()["is_admin"] is True
