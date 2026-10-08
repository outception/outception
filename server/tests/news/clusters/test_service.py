import pytest
from sqlalchemy import func, select

from outception.models import NewsCluster, NewsClusterMember
from outception.news.clusters import service
from outception.news.clusters.urlkey import url_key
from outception.news.schemas import NewsItem
from outception.postgres import AsyncSession
from outception.redis import Redis


def _item(url: str, title: str, teaser: str | None = None) -> NewsItem:
    return NewsItem(id=url, title=title, url=url, teaser=teaser)


async def _count(session: AsyncSession, model: type[object]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
class TestIngest:
    async def test_same_link_joins_by_url_key(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        first = await clusterer.ingest(
            "bbc-world",
            [
                _item(
                    "https://example.com/story?utm_source=rss",
                    "Council backs riverside plan",
                )
            ],
        )
        second = await clusterer.ingest(
            "guardian",
            [
                _item(
                    "https://www.example.com/story/",
                    "Riverside plan approved by council",
                )
            ],
        )
        assert first.created == 1
        assert second.joined_by_url == 1
        assert await _count(session, NewsCluster) == 1
        assert await _count(session, NewsClusterMember) == 2
        cluster = await session.scalar(select(NewsCluster))
        assert cluster is not None
        assert cluster.publisher_count == 2
        assert cluster.lead_source_id == "bbc-world"
        found = await service.cluster_for_urls(redis, ["https://example.com/story"])
        assert found == {"https://example.com/story": (str(cluster.id), 2)}

    async def test_near_duplicate_headline_joins_by_text(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        headline = "Central bank holds rates at 4.25 percent as two members vote for a cut citing the labour market"
        await clusterer.ingest("reuters", [_item("https://a.example/1", headline)])
        stats = await clusterer.ingest(
            "bbc-business",
            [_item("https://b.example/2", headline + " and wage growth")],
        )
        assert stats.joined_by_text == 1
        assert await _count(session, NewsCluster) == 1

    async def test_different_story_makes_a_new_cluster(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        await clusterer.ingest(
            "reuters",
            [_item("https://a.example/1", "Central bank holds rates at 4.25 percent")],
        )
        stats = await clusterer.ingest(
            "bbc-sport",
            [_item("https://b.example/2", "Holders out of the cup on penalties")],
        )
        assert stats.created == 1
        assert stats.borderline == 0
        assert await _count(session, NewsCluster) == 2

    async def test_same_item_twice_is_one_member(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        item = _item("https://a.example/1", "A headline about something")
        await clusterer.ingest("reuters", [item])
        await clusterer.ingest("reuters", [item])
        assert await _count(session, NewsClusterMember) == 1

    async def test_undo_takes_back_only_what_a_failed_ingest_wrote(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        kept_url = "https://example.com/kept"
        await clusterer.ingest(
            "bbc-world", [_item(kept_url, "Council backs riverside plan")]
        )
        kept_key = service.URL_KEY.format(sha=url_key(kept_url))
        kept = await redis.get(kept_key)
        assert kept is not None
        # The next ingest joins the kept story, creates another, and fails.
        await clusterer.ingest(
            "guardian",
            [
                _item(kept_url, "Council backs riverside plan"),
                _item(
                    "https://other.example/new", "Storm closes the harbour for a week"
                ),
            ],
        )
        [(created, _)] = clusterer._created
        await clusterer.undo()
        # The lookup that was there before stays; the new one goes.
        assert await redis.get(kept_key) == kept
        assert (
            await redis.get(
                service.URL_KEY.format(sha=url_key("https://other.example/new"))
            )
            is None
        )
        assert await redis.get(service.SIG_KEY.format(cluster_id=created)) is None
        # No band still offers the vanished cluster as a candidate.
        for band in await redis.keys("news:cluster:lsh*"):
            assert str(created) not in await redis.smembers(band)

    async def test_merge_moves_members_and_repoints_lookups(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        clusterer = service.Clusterer(session, redis)
        await clusterer.ingest(
            "reuters", [_item("https://a.example/1", "Rates held at 4.25 percent")]
        )
        await clusterer.ingest(
            "bbc",
            [_item("https://b.example/2", "Bank leaves interest rates unchanged")],
        )
        clusters = list((await session.execute(select(NewsCluster))).scalars().all())
        assert len(clusters) == 2
        keep, drop = clusters
        moved = await clusterer.merge(keep.id, drop.id)
        assert moved == 1
        assert await _count(session, NewsCluster) == 1
        assert await _count(session, NewsClusterMember) == 2
        found = await service.cluster_for_urls(redis, ["https://b.example/2"])
        assert found["https://b.example/2"] == (str(keep.id), 2)
        assert await redis.get(
            service.URL_KEY.format(sha=url_key("https://b.example/2"))
        ) == str(keep.id)

    async def test_merge_into_a_vanished_keeper_is_a_no_op(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        # The keeper of a queued borderline pair can be folded away before
        # the pair is resolved: the merge must not move members into a
        # cluster that no longer exists.
        clusterer = service.Clusterer(session, redis)
        await clusterer.ingest(
            "reuters", [_item("https://a.example/1", "Rates held at 4.25 percent")]
        )
        await clusterer.ingest(
            "bbc",
            [_item("https://b.example/2", "Bank leaves interest rates unchanged")],
        )
        keep, drop = list((await session.execute(select(NewsCluster))).scalars().all())
        await session.delete(keep)
        await session.flush()
        assert await clusterer.merge(keep.id, drop.id) == 0
        assert await _count(session, NewsCluster) == 1
        assert await _count(session, NewsClusterMember) == 1

    async def test_pending_round_trip(self, redis: Redis) -> None:
        await service.note_pending(redis, "bbc-world")
        await service.note_pending(redis, "bbc-world")
        assert await service.pop_pending(redis, 10) == ["bbc-world"]
        assert await service.pop_pending(redis, 10) == []
