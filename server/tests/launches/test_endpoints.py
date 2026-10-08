from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

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
        # Before approval only the submitter sees it (the public read is
        # covered below, where an unknown id gives nothing away).
        assert (await client.get(f"/v1/launches/{launch['id']}")).status_code == 200
        # Review is for the admin list only.
        assert (await client.get("/v1/launches/review")).status_code == 403
        assert (
            await client.post(f"/v1/launches/{launch['id']}/withdraw")
        ).status_code == 204
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

    @pytest.mark.auth
    async def test_owner_edits_withdraws_resubmits_and_deletes(
        self, client: AsyncClient, user: User
    ) -> None:
        launch = (await client.post("/v1/launches", json=BODY)).json()
        # Edit while waiting: the copy changes, the state does not.
        edited = await client.patch(
            f"/v1/launches/{launch['id']}", json={"name": "Widget Pro"}
        )
        assert edited.status_code == 200, edited.text
        assert edited.json()["name"] == "Widget Pro"
        assert edited.json()["state"] == "submitted"
        # The owner sees it before listing; the public does not.
        own = await client.get(f"/v1/launches/{launch['id']}")
        assert own.status_code == 200
        # Withdraw, then an edit puts it back into the queue.
        assert (
            await client.post(f"/v1/launches/{launch['id']}/withdraw")
        ).status_code == 204
        mine = (await client.get("/v1/launches/mine")).json()
        assert mine[0]["state"] == "withdrawn"
        back = await client.patch(
            f"/v1/launches/{launch['id']}", json={"tagline": "Widgets, but better"}
        )
        assert back.json()["state"] == "submitted"
        assert back.json()["reviewer_note"] is None
        # Delete removes it for good.
        assert (await client.delete(f"/v1/launches/{launch['id']}")).status_code == 204
        assert (await client.get("/v1/launches/mine")).json() == []
        assert (await client.get(f"/v1/launches/{launch['id']}")).status_code == 404

    @pytest.mark.auth
    async def test_listed_product_counts_views_and_clicks(
        self,
        client: AsyncClient,
        user: User,
        redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "ADMIN_EMAILS", [user.email])
        launch = (await client.post("/v1/launches", json=BODY)).json()
        today = datetime.now(UTC).date().isoformat()
        await client.post(f"/v1/launches/{launch['id']}/approve", json={"day": today})
        # The wall shows it twice, a reader opens it once.
        for _ in range(2):
            beacon = await client.post(
                "/v1/launches/views", json={"ids": [launch["id"]]}
            )
            assert beacon.status_code == 204, beacon.text
        go = await client.get(f"/v1/launches/{launch['id']}/go", follow_redirects=False)
        assert go.status_code == 302
        assert go.headers["Location"] == BODY["url"]
        assert go.headers["Cache-Control"] == "no-store"
        stats = await client.get(f"/v1/launches/{launch['id']}/stats")
        assert stats.status_code == 200, stats.text
        assert stats.json()["views"] == 2
        assert stats.json()["clicks"] == 1
        assert stats.json()["days"][0]["day"] == today
        mine = (await client.get("/v1/launches/mine")).json()
        assert (mine[0]["views"], mine[0]["clicks"]) == (2, 1)
        # The card opens the product through the counting redirect.
        mocker.patch.object(products, "_client", return_value=redis)
        card = (await client.get("/v1/news/products-of-the-day")).json()
        assert card["items"][1]["url"].endswith(f"/v1/launches/{launch['id']}/go")
        # A listed product can only be withdrawn, not edited or deleted.
        assert (
            await client.patch(f"/v1/launches/{launch['id']}", json={"name": "X Y"})
        ).status_code == 400
        assert (await client.delete(f"/v1/launches/{launch['id']}")).status_code == 400

    async def test_unlisted_ids_count_nothing_and_cannot_be_opened(
        self, client: AsyncClient
    ) -> None:
        from uuid import uuid4

        unknown = str(uuid4())
        beacon = await client.post("/v1/launches/views", json={"ids": [unknown]})
        assert beacon.status_code == 204
        assert (
            await client.get(f"/v1/launches/{unknown}/go", follow_redirects=False)
        ).status_code == 404
        assert (await client.get(f"/v1/launches/{unknown}/stats")).status_code == 401


@pytest.mark.asyncio
class TestRaceRoutes:
    @pytest.mark.auth
    async def test_my_race_races_views_against_clicks_for_one_product(
        self, client: AsyncClient, user: User, session: AsyncSession
    ) -> None:
        from outception.launches import service

        launch = (await client.post("/v1/launches", json=BODY)).json()
        today = datetime.now(UTC).date()
        await service._bump(session, UUID(launch["id"]), today, views=3, clicks=1)
        await session.commit()
        race = await client.get("/v1/launches/mine/race")
        assert race.status_code == 200, race.text
        body = race.json()
        assert body["mode"] == "reach"
        last = [r for r in body["rows"] if r["date"] == today.isoformat()]
        assert {r["name"]: r["value"] for r in last} == {"views": 3, "clicks": 1}
        # The race opens on the first day with a value: today, here.
        assert len(body["rows"]) == 2

    @pytest.mark.auth
    async def test_my_race_is_empty_without_reach(
        self, client: AsyncClient, user: User
    ) -> None:
        await client.post("/v1/launches", json=BODY)
        race = await client.get("/v1/launches/mine/race")
        assert race.status_code == 200
        assert race.json() == {"mode": "reach", "rows": []}

    @pytest.mark.auth
    async def test_two_products_race_each_other_with_visible_labels(
        self, client: AsyncClient, user: User, session: AsyncSession
    ) -> None:
        from outception.launches import service

        first = (await client.post("/v1/launches", json=BODY)).json()
        second = (await client.post("/v1/launches", json=BODY)).json()
        today = datetime.now(UTC).date()
        await service._bump(session, UUID(first["id"]), today, views=5)
        await service._bump(session, UUID(second["id"]), today, views=2)
        await session.commit()
        body = (await client.get("/v1/launches/mine/race")).json()
        assert body["mode"] == "products"
        assert {r["name"]: r["value"] for r in body["rows"]} == {
            "Widget": 5,
            "Widget (2)": 2,
        }

    async def test_my_race_needs_a_login(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/launches/mine/race")).status_code == 401

    @pytest.mark.auth
    async def test_visits_race_is_for_the_admin_list(
        self, client: AsyncClient, user: User, mocker: MockerFixture
    ) -> None:
        assert (await client.get("/v1/launches/visits/race")).status_code == 403
        mocker.patch.object(settings, "ADMIN_EMAILS", [user.email])
        race = await client.get("/v1/launches/visits/race?dimension=country")
        assert race.status_code == 200, race.text
        assert race.json() == {"mode": "visits", "rows": []}
        assert (
            await client.get("/v1/launches/visits/race?dimension=x")
        ).status_code == 422
