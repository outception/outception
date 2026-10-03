from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.models import User
from outception.news.sources import products
from outception.postgres import AsyncSession
from outception.redis import Redis

BODY = {
    "name": "Widget",
    "tagline": "Widgets, but smaller",
    "url": "https://example.com/widget",
    "kicker": "new",
    "description": "A small widget.",
    "contact_email": "maker@example.com",
}


@pytest.fixture(autouse=True)
def _no_network(mocker: MockerFixture) -> None:
    mocker.patch(
        "outception.launches.service.is_fetchable_async", AsyncMock(return_value=True)
    )
    mocker.patch(
        "outception.launches.service.fetch_bytes", AsyncMock(return_value=b"ok")
    )


@pytest.mark.asyncio
class TestLaunchRoutes:
    async def test_archive_is_public_and_cacheable(self, client: AsyncClient) -> None:
        response = await client.get("/v1/launches")
        assert response.status_code == 200
        assert response.json() == {"days": []}
        assert response.headers["Cache-Control"].startswith("public")
        etag = response.headers["ETag"]
        again = await client.get("/v1/launches", headers={"If-None-Match": etag})
        assert again.status_code == 304

    async def test_submit_needs_a_login(self, client: AsyncClient) -> None:
        response = await client.post("/v1/launches", json=BODY)
        assert response.status_code == 401

    @pytest.mark.auth
    async def test_submit_withdraw_and_mine(
        self, client: AsyncClient, user: User, session: AsyncSession
    ) -> None:
        response = await client.post("/v1/launches", json=BODY)
        assert response.status_code == 201, response.text
        launch = response.json()
        assert launch["state"] == "submitted"
        assert "contact_email" in launch
        mine = await client.get("/v1/launches/mine")
        assert [item["id"] for item in mine.json()] == [launch["id"]]
        # Not visible before approval, to anyone.
        assert (await client.get(f"/v1/launches/{launch['id']}")).status_code == 404
        # Review is for the admin list only.
        assert (await client.get("/v1/launches/review")).status_code == 403
        assert (await client.delete(f"/v1/launches/{launch['id']}")).status_code == 204
        mine = await client.get("/v1/launches/mine")
        assert mine.json()[0]["state"] == "withdrawn"

    @pytest.mark.auth
    async def test_admin_approves_into_a_day(
        self,
        client: AsyncClient,
        user: User,
        session: AsyncSession,
        redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "ADMIN_EMAILS", [user.email])
        launch = (await client.post("/v1/launches", json=BODY)).json()
        queue = await client.get("/v1/launches/review")
        assert queue.status_code == 200
        assert [item["id"] for item in queue.json()["items"]] == [launch["id"]]
        today = datetime.now(UTC).date().isoformat()
        approved = await client.post(
            f"/v1/launches/{launch['id']}/approve",
            json={"day": today, "featured": True},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["state"] == "live"
        assert approved.json()["position"] == 1
        archive = (await client.get("/v1/launches")).json()
        assert archive["days"][0]["day"] == today
        assert archive["days"][0]["items"][0]["name"] == "Widget"
        public = await client.get(f"/v1/launches/{launch['id']}")
        assert public.status_code == 200
        assert "contact_email" not in public.json()
        # The card serves it through the ordinary source route.
        mocker.patch.object(products, "_client", return_value=redis)
        card = await client.get("/v1/news/products-of-the-day")
        assert card.status_code == 200, card.text
        titles = [item["title"] for item in card.json()["items"]]
        assert titles[0].startswith("outception.ai:")
        assert titles[1] == "Widget: Widgets, but smaller"

    @pytest.mark.auth
    async def test_rejected_products_carry_the_note_to_the_owner(
        self, client: AsyncClient, user: User, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ADMIN_EMAILS", [user.email])
        launch = (await client.post("/v1/launches", json=BODY)).json()
        rejected = await client.post(
            f"/v1/launches/{launch['id']}/reject", json={"note": "Not yet"}
        )
        assert rejected.status_code == 200
        mine = (await client.get("/v1/launches/mine")).json()
        assert mine[0]["state"] == "rejected"
        assert mine[0]["reviewer_note"] == "Not yet"
