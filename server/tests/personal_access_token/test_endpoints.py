import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreatePersonalAccessToken:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/personal_access_tokens/",
            json={"comment": "ci", "scopes": ["user:read"]},
        )
        assert response.status_code == 401

    @pytest.mark.auth
    async def test_create_returns_token_once(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/personal_access_tokens/",
            json={"comment": "ci token", "scopes": ["user:read"]},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["token"].startswith("polar_pat_")
        pat = body["personal_access_token"]
        assert pat["comment"] == "ci token"
        assert pat["scopes"] == ["user:read"]
        assert pat["expires_at"] is None
        # The raw token must not appear on the persisted resource view.
        assert "token" not in pat

    @pytest.mark.auth
    async def test_rejects_empty_scopes(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/personal_access_tokens/",
            json={"comment": "x", "scopes": []},
        )
        assert response.status_code == 422

    @pytest.mark.auth
    async def test_rejects_non_positive_expiry(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/personal_access_tokens/",
            json={"comment": "x", "scopes": ["user:read"], "expires_in": -3600},
        )
        assert response.status_code == 422
