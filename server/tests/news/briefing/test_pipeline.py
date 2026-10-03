"""The scorer and the builder against a fake chain, end to end through
the routes."""

import json
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select

from outception.config import settings
from outception.kit.utils import utc_now
from outception.models import JobRun, NewsCluster, NewsClusterScore, User
from outception.news.briefing import builder, scorer
from outception.news.briefing.profiles import profiles
from outception.news.briefing.tasks import route_recent
from outception.news.clusters import service as clusters
from outception.news.schemas import NewsItem
from outception.news.summaries.providers.base import (
    Answer,
    Decision,
    Question,
    QuestionKind,
    Reply,
)
from outception.news.summaries.providers.chain import ChainExhausted
from outception.news.summaries.providers.lanes import Lane
from outception.postgres import AsyncSession
from outception.redis import Redis


class FakeChains:
    def __init__(
        self,
        score: str = "8",
        category: str = "security",
        why: str = "Patch 2.4.1 now.",
    ) -> None:
        self.score, self.category, self.why = score, category, why
        self.decisions: list[dict[str, Any]] = []
        self.exhausted = False

    async def decide(
        self, task: str, state: dict[str, Any], questions: list[Question], **kwargs: Any
    ) -> Decision:
        if self.exhausted:
            raise ChainExhausted(Lane.background)
        self.decisions.append(state)
        answers = {}
        for question in questions:
            if question.id == "score":
                answers["score"] = Answer(
                    QuestionKind.score, {self.score: 1.0}, self.score, float(self.score)
                )
            elif question.id == "category":
                answers["category"] = Answer(
                    QuestionKind.choice, {self.category: 1.0}, self.category
                )
            else:
                answers[question.id] = Answer(QuestionKind.bool, {"true": 1.0}, "true")
        return Decision(
            answers=answers, model="fake-model", latency_ms=3, calibrated=False
        )

    async def generate(self, prompt: str, lane: Lane, **kwargs: Any) -> Reply:
        return Reply(text=f'"{self.why}" — said nobody', model="fake-model")

    async def available(self, lane: Lane) -> bool:
        return True


async def _seed(
    session: AsyncSession, redis: Redis, title: str, sources: list[str]
) -> UUID:
    clusterer = clusters.Clusterer(session, redis)
    for index, source in enumerate(sources):
        slug = abs(hash(title)) % 10_000_000
        await clusterer.ingest(
            source,
            [
                NewsItem(
                    id=f"{title}-{index}",
                    title=title,
                    url=f"https://{source}.example/{slug}/{index}",
                )
            ],
        )
    row = await session.execute(select(NewsCluster).where(NewsCluster.title == title))
    cluster = row.scalar_one()
    return cluster.id


@pytest.mark.asyncio
class TestScorer:
    async def test_scores_pending_clusters_through_the_chain(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        fake = FakeChains()
        mocker.patch.object(scorer, "build_chains", return_value=fake)
        developer = profiles()["developer"]
        cluster_id = await _seed(
            session,
            redis,
            "Version 2.4.1 fixes remote code execution flaw",
            ["hackernews", "theverge"],
        )
        await scorer.note_pending(redis, "developer", [cluster_id])
        stats = await scorer.score_pending(session, redis, developer)
        assert (stats.scored, stats.nulls) == (1, 0)
        row = await session.get(NewsClusterScore, (cluster_id, "developer"))
        assert row is not None
        assert (row.score, row.category) == (8, "security")
        assert (
            row.why == "Patch 2.4.1 now. , said nobody"
        )  # scrubbed of quotes and dashes
        assert row.provider == "fake-model"
        state = fake.decisions[0]
        assert state["publisher_count"] == 2
        assert "policy" in state
        assert "Levels" in state["policy"]
        runs = list((await session.execute(select(JobRun))).scalars().all())
        assert [run.kind for run in runs] == ["score"]
        assert runs[0].served_model == "fake-model"
        # Scored within a day: not scored again.
        await scorer.note_pending(redis, "developer", [cluster_id])
        again = await scorer.score_pending(session, redis, developer)
        assert again.scored == 1
        assert len(fake.decisions) == 1

    async def test_exhausted_lane_leaves_the_rest_pending(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        fake = FakeChains()
        fake.exhausted = True
        mocker.patch.object(scorer, "build_chains", return_value=fake)
        cluster_id = await _seed(session, redis, "Something happened", ["hackernews"])
        await scorer.note_pending(redis, "developer", [cluster_id])
        stats = await scorer.score_pending(session, redis, profiles()["developer"])
        assert stats.deferred
        assert await redis.scard(scorer.PENDING_KEY.format(profile="developer")) == 1

    async def test_routing_puts_recent_clusters_on_their_profiles(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        await _seed(session, redis, "A developer story", ["hackernews"])
        await _seed(session, redis, "A sports story", ["bbcsport"])
        routed = await route_recent(session, redis)
        assert routed >= 2
        assert await redis.scard(scorer.PENDING_KEY.format(profile="developer")) == 1
        assert await redis.scard(scorer.PENDING_KEY.format(profile="sports")) == 1


@pytest.mark.asyncio
class TestBuilderAndRoutes:
    async def test_build_then_serve(
        self,
        session: AsyncSession,
        redis: Redis,
        client: AsyncClient,
        mocker: MockerFixture,
    ) -> None:
        developer = profiles()["developer"]
        fake = FakeChains()
        mocker.patch.object(scorer, "build_chains", return_value=fake)
        high = await _seed(
            session,
            redis,
            "Version 2.4.1 fixes remote code execution flaw",
            ["hackernews", "theverge"],
        )
        low = await _seed(session, redis, "Small library ships a patch", ["hackernews"])
        await scorer.note_pending(redis, "developer", [high])
        await scorer.score_pending(session, redis, developer)
        fake.score = "3"
        await scorer.note_pending(redis, "developer", [low])
        await scorer.score_pending(session, redis, developer)
        before = await client.get("/v1/news/briefing/developer")
        assert before.status_code == 404
        built = await builder.build(session, redis, developer)
        assert built is not None
        assert [item["title"] for item in built.items] == [
            "Version 2.4.1 fixes remote code execution flaw"
        ]
        assert built.stats["per_category"] == {"security": 1}
        await session.commit()
        response = await client.get("/v1/news/briefing/developer")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "success"
        assert body["profile"] == "developer"
        item = body["items"][0]
        assert item["publisherCount"] == 2
        assert item["category"] == "security"
        assert item["why"] == "Patch 2.4.1 now. , said nobody"
        assert item["leadSourceName"] == "Hacker News"
        assert item["item"]["url"].startswith("https://hackernews.example/")
        etag = response.headers["ETag"]
        assert (
            await client.get(
                "/v1/news/briefing/developer", headers={"If-None-Match": etag}
            )
        ).status_code == 304
        history = await client.get(
            "/v1/news/briefing/developer/history", params={"days": 7}
        )
        assert history.status_code == 200
        assert len(history.json()["days"]) == 1
        assert (await client.get("/v1/news/briefing/no-such")).status_code == 404

    async def test_quota_and_threshold(self) -> None:
        developer = profiles()["developer"]
        from outception.cards.schemas import BriefingItem

        def item(index: int, score: int, category: str) -> BriefingItem:
            return BriefingItem.model_validate(
                {
                    "clusterId": str(index),
                    "title": f"t{index}",
                    "url": "https://x/",
                    "score": score,
                    "category": category,
                    "publisherCount": 1,
                    "leadSourceName": "x",
                    "item": {
                        "id": str(index),
                        "title": f"t{index}",
                        "url": "https://x/",
                    },
                }
            )

        candidates = [item(i, 9, "security") for i in range(8)] + [
            item(99, 5, "security"),
            item(100, 8, "launches"),
        ]
        chosen, taken = builder.select_items(developer, candidates)
        assert taken == {"security": 6, "launches": 1}
        assert len(chosen) == 7
        assert all((c.score or 0) >= developer.min_score for c in chosen)

    async def test_profiles_route_and_stale_status(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        response = await client.get("/v1/news/briefing/profiles")
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()["profiles"]]
        assert "developer" in ids
        old = int((utc_now() - timedelta(hours=3)).timestamp() * 1000)
        await redis.set(
            builder.LATEST_KEY.format(profile="sports"),
            json.dumps(
                {
                    "profile": "sports",
                    "builtAt": old,
                    "staleAfterMs": builder.STALE_AFTER_MS,
                    "items": [],
                }
            ),
        )
        stale = await client.get("/v1/news/briefing/sports")
        assert stale.json()["status"] == "cache"

    @pytest.mark.auth
    async def test_me_routes(self, client: AsyncClient, user: User) -> None:
        assert (await client.get("/v1/news/briefing/me")).json() == {"profiles": []}
        assert (await client.put("/v1/news/briefing/me/developer")).status_code == 204
        assert (await client.put("/v1/news/briefing/me/nope")).status_code == 404
        assert (await client.put("/v1/news/briefing/me/sports")).status_code == 204
        assert (await client.get("/v1/news/briefing/me")).json() == {
            "profiles": ["developer", "sports"]
        }
        assert (
            await client.delete("/v1/news/briefing/me/developer")
        ).status_code == 204
        assert (await client.get("/v1/news/briefing/me")).json() == {
            "profiles": ["sports"]
        }

    async def test_tasks_are_gated(self, mocker: MockerFixture) -> None:
        from outception.news.briefing import tasks

        mocker.patch.object(settings, "BRIEFING_ENABLED", False)
        redis_factory = mocker.patch("outception.news.briefing.tasks.create_redis")
        await tasks.score_clusters()
        await tasks.build_briefing()
        redis_factory.assert_not_called()
