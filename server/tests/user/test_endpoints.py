import pytest
from httpx import AsyncClient

from outception.models import User
from outception.models.user import OAuthAccount
from tests.fixtures.auth import AuthSubjectFixture


@pytest.mark.asyncio
class TestGetAuthenticated:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user(self, client: AsyncClient, user: User) -> None:
        response = await client.get("/v1/users/me")

        assert response.status_code == 200
        json = response.json()
        assert json["id"] == str(user.id)
        assert json["email"] == user.email
        assert json["oauth_accounts"] == []
        assert "organizations" not in json

    @pytest.mark.auth
    async def test_user_with_social_account(
        self, client: AsyncClient, user: User, user_google_oauth: OAuthAccount
    ) -> None:
        response = await client.get("/v1/users/me")

        assert response.status_code == 200
        accounts = response.json()["oauth_accounts"]
        assert [account["platform"] for account in accounts] == ["google"]


@pytest.mark.asyncio
class TestUpdateAuthenticated:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.patch("/v1/users/me", json={"first_name": "Jane"})

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user(self, client: AsyncClient, user: User) -> None:
        response = await client.patch(
            "/v1/users/me",
            json={"first_name": "Jane", "accepted_terms_of_service": True},
        )

        assert response.status_code == 200
        json = response.json()
        assert json["first_name"] == "Jane"
        assert json["accepted_terms_of_service"] is True


@pytest.mark.asyncio
class TestScopes:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/users/me/scopes")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user(self, client: AsyncClient) -> None:
        response = await client.get("/v1/users/me/scopes")

        assert response.status_code == 200
        assert "user:read" in response.json()["scopes"]


@pytest.mark.asyncio
class TestDeleteAuthenticated:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.delete("/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user(self, client: AsyncClient, user: User) -> None:
        response = await client.delete("/v1/users/me")

        assert response.status_code == 200
        assert response.json() == {"deleted": True}
        assert user.deleted_at is not None
        assert user.email != user.email.lower() or "@" in user.email


@pytest.mark.asyncio
class TestDisconnectOAuthAccount:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.delete("/v1/users/me/oauth-accounts/google")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_connected(self, client: AsyncClient) -> None:
        response = await client.delete("/v1/users/me/oauth-accounts/google")

        assert response.status_code == 404

    @pytest.mark.auth(AuthSubjectFixture(subject="user"))
    async def test_disconnect(
        self, client: AsyncClient, user: User, user_google_oauth: OAuthAccount
    ) -> None:
        response = await client.delete("/v1/users/me/oauth-accounts/google")

        assert response.status_code == 204
