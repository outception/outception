from datetime import date

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select

from outception.config import settings
from outception.models import PushSubscription
from outception.news.briefing import push, service
from outception.news.briefing.profiles import profiles
from outception.news.briefing.schemas import BriefingResponse, PushSubscribe
from outception.postgres import AsyncSession
from outception.redis import Redis

ENDPOINT = "https://push.example/send/abc123"
KEYS = {"p256dh": "p" * 32, "auth": "a" * 16}


def _profile():  # type: ignore[no-untyped-def]
    return profiles()["developer"]


def _briefing(n: int = 3) -> BriefingResponse:
    items = [
        {
            "clusterId": f"c{i}",
            "title": f"Story {i}",
            "url": f"https://example.org/{i}",
            "category": "Tools",
            "publisherCount": 2,
            "leadSourceName": "Example",
            "item": {
                "id": f"i{i}",
                "title": f"Story {i}",
                "url": f"https://example.org/{i}",
            },
        }
        for i in range(n)
    ]
    return BriefingResponse.model_validate(
        {
            "status": "success",
            "profile": "developer",
            "builtAt": 1,
            "staleAfterMs": 1,
            "items": items,
        }
    )


@pytest.mark.asyncio
class TestRoutes:
    async def test_subscribe_upserts_and_unsubscribe_removes(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        body = {"kind": "web", "endpoint": ENDPOINT, "keys": KEYS}
        for _ in range(2):
            response = await client.post(
                "/v1/news/briefing/developer/subscribe", json=body
            )
            assert response.status_code == 204, response.text
        rows = (await session.execute(select(PushSubscription))).scalars().all()
        assert len(rows) == 1
        assert rows[0].kind == "web"
        assert rows[0].keys == KEYS
        response = await client.request(
            "DELETE",
            "/v1/news/briefing/developer/subscribe",
            json={"endpoint": ENDPOINT},
        )
        assert response.status_code == 204
        assert (await session.execute(select(PushSubscription))).scalars().all() == []

    async def test_unknown_profile_is_404(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/news/briefing/nope/subscribe",
            json={"kind": "app", "endpoint": "ExponentPushToken[xxxxxxxx]"},
        )
        assert response.status_code == 404

    async def test_profiles_carry_the_public_key_only_when_configured(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        response = await client.get("/v1/news/briefing/profiles")
        assert response.json()["pushPublicKey"] is None
        mocker.patch.object(settings, "WEB_PUSH_VAPID_PUBLIC_KEY", "pub")
        mocker.patch.object(settings, "WEB_PUSH_VAPID_PRIVATE_KEY", "priv")
        mocker.patch.object(settings, "WEB_PUSH_SUBJECT", "mailto:x@example.com")
        assert service.profile_list().push_public_key == "pub"


@pytest.mark.asyncio
class TestSend:
    async def test_one_push_per_day_and_gone_rows_drop(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        profile = _profile()
        mocker.patch.object(service, "latest", return_value=_briefing())
        await push.subscribe(
            session,
            profile,
            PushSubscribe(kind="web", endpoint=ENDPOINT, keys=KEYS),  # type: ignore[arg-type]
        )
        await push.subscribe(
            session,
            profile,
            PushSubscribe(kind="app", endpoint="ExponentPushToken[dead]"),
        )
        deliver = mocker.patch.object(
            push,
            "deliver",
            side_effect=lambda row, m: "gone" if row.kind == "app" else "delivered",
        )
        today = date(2026, 10, 6)
        counts = await push.send_profile(session, redis, profile, today)
        assert counts == {"delivered": 1, "gone": 1, "failed": 0}
        message = deliver.call_args_list[0].args[1]
        assert message["title"] == "Developer briefing"
        assert message["body"] == "Story 0 and 2 more"
        assert message["url"] == "/briefing/developer"
        rows = (await session.execute(select(PushSubscription))).scalars().all()
        assert [r.kind for r in rows] == ["web"]
        assert rows[0].last_sent_for == today
        # The same morning again: nothing is due.
        assert await push.send_profile(session, redis, profile, today) == {
            "delivered": 0,
            "gone": 0,
            "failed": 0,
        }
        assert deliver.call_count == 2

    async def test_repeated_failures_drop_the_row(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        profile = _profile()
        mocker.patch.object(service, "latest", return_value=_briefing(1))
        mocker.patch.object(push, "deliver", return_value="failed")
        await push.subscribe(
            session,
            profile,
            PushSubscribe(kind="app", endpoint="ExponentPushToken[flaky]"),
        )
        for day in range(1, push.MAX_FAILURES + 1):
            await push.send_profile(session, redis, profile, date(2026, 10, day))
        assert (await session.execute(select(PushSubscription))).scalars().all() == []

    async def test_nothing_built_sends_nothing(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        deliver = mocker.patch.object(push, "deliver")
        await push.subscribe(
            session,
            _profile(),
            PushSubscribe(kind="app", endpoint="ExponentPushToken[x]"),
        )
        assert await push.send_profile(session, redis, _profile()) == {
            "delivered": 0,
            "gone": 0,
            "failed": 0,
        }
        deliver.assert_not_called()


class TestWebProvider:
    def test_send_without_keys_fails_closed(self) -> None:
        from outception.news.briefing.providers import web

        assert web.send(ENDPOINT, None, {"title": "x"}) == "failed"
