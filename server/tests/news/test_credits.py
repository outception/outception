import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreditsEndpoint:
    async def test_lists_every_upstream_with_its_terms(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/v1/news/credits")
        assert response.status_code == 200
        assert "public" in response.headers["cache-control"]
        credits = response.json()["credits"]
        assert len(credits) >= 5
        ids = {row["id"] for row in credits}
        assert "open-meteo" in ids
        for row in credits:
            assert set(row) == {"id", "name", "url", "terms", "used_for"}
            assert row["url"].startswith("https://")
            assert row["terms"]
            assert row["used_for"]
