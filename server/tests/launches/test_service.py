from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from outception.config import settings
from outception.exceptions import BadRequest, NotPermitted
from outception.launches import service
from outception.launches.schemas import (
    LaunchApprove,
    LaunchCreate,
    LaunchEdit,
    LaunchUpdate,
)
from outception.models import Launch, LaunchStatus, User
from outception.news import cache as news_cache
from outception.postgres import AsyncSession
from outception.redis import Redis


def _body(name: str = "Widget", **overrides: object) -> LaunchCreate:
    fields: dict[str, object] = {
        "name": name,
        "tagline": "Widgets, but smaller",
        "url": "https://example.com/widget",
        "kicker": "new",
        "description": "A small widget. Write to me at a@b.io.",
        "contact_email": "maker@example.com",
    }
    fields.update(overrides)
    return LaunchCreate.model_validate(fields)


@pytest.fixture(autouse=True)
def _no_network(mocker: MockerFixture) -> None:
    mocker.patch(
        "outception.launches.service.is_fetchable_async", AsyncMock(return_value=True)
    )
    mocker.patch(
        "outception.launches.service.fetch_bytes",
        AsyncMock(return_value=b"<html>ok</html>"),
    )


@pytest.mark.asyncio
class TestSubmitAndReview:
    async def test_submission_is_scrubbed_and_invisible(
        self, session: AsyncSession, user: User
    ) -> None:
        launch = await service.submit(session, user, _body())
        assert launch.state == LaunchStatus.submitted
        assert "[email]" in launch.description
        assert await service.archive(session) == []
        mine = await service.mine(session, user)
        assert [item.id for item in mine] == [launch.id]

    def test_mail_text_is_escaped_and_single_line(self) -> None:
        launch = Launch(
            name='<a href="https://evil.example">Review</a>',
            tagline="Tag\r\nline",
            url="https://example.com/x",
            kicker="new",
            description="",
            contact_email="a@b.io",
            state=LaunchStatus.submitted,
        )
        details = service._details(launch)
        assert '<a href="https://evil.example">' not in details
        assert "&lt;a href=" in details
        assert service._subject(f"New: {launch.tagline}") == "New: Tag line"

    def test_blocklist_sees_through_ports_userinfo_and_subdomains(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            service, "blocked_domains", return_value=frozenset({"example.com"})
        )
        for url in (
            "https://example.com/",
            "https://user@example.com/",
            "https://example.com:8443/",
            "https://news.example.com/",
            "https://www.example.com/",
        ):
            assert service._blocked(url), url
        assert not service._blocked("https://example.org/")
        assert not service._blocked("https://notexample.com/")

    async def test_blocked_domain_is_refused(
        self, session: AsyncSession, user: User, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            service, "blocked_domains", return_value=frozenset({"example.com"})
        )
        with pytest.raises(BadRequest):
            await service.submit(session, user, _body())

    async def test_withdraw_only_your_own_submitted(
        self, session: AsyncSession, redis: Redis, user: User, user_second: User
    ) -> None:
        launch = await service.submit(session, user, _body())
        with pytest.raises(NotPermitted):
            await service.withdraw(session, redis, user_second, launch.id)
        await service.withdraw(session, redis, user, launch.id)
        assert launch.state == LaunchStatus.withdrawn
        with pytest.raises(BadRequest):
            await service.withdraw(session, redis, user, launch.id)
        # Only the owner edits or deletes, and an edit resubmits.
        with pytest.raises(NotPermitted):
            await service.delete(session, user_second, launch.id)
        back = await service.update(
            session, redis, user, launch.id, LaunchUpdate(name="Widget two")
        )
        assert back.state == LaunchStatus.submitted
        assert back.name == "Widget two"
        await service.delete(session, user, launch.id)
        assert await service.mine(session, user) == []

    async def test_a_day_holds_five(
        self, session: AsyncSession, redis: Redis, user: User
    ) -> None:
        day = datetime.now(UTC).date() + timedelta(days=1)
        launches = [
            await service.submit(session, user, _body(f"P{i}")) for i in range(6)
        ]
        for launch in launches[:5]:
            approved = await service.approve(
                session, redis, launch.id, LaunchApprove(day=day)
            )
            assert approved.state == LaunchStatus.approved
        assert [launch.position for launch in launches[:5]] == [1, 2, 3, 4, 5]
        with pytest.raises(BadRequest, match="already has its 5"):
            await service.approve(
                session, redis, launches[5].id, LaunchApprove(day=day)
            )
        assert (await service.slots_taken(session))[day.isoformat()] == 5

    async def test_today_goes_live_at_once_and_builds_the_card(
        self, session: AsyncSession, redis: Redis, user: User
    ) -> None:
        today = datetime.now(UTC).date()
        launch = await service.submit(session, user, _body("Live one"))
        featured = await service.submit(session, user, _body("Star"))
        await service.approve(session, redis, launch.id, LaunchApprove(day=today))
        await service.approve(
            session, redis, featured.id, LaunchApprove(day=today, featured=True)
        )
        assert launch.state == LaunchStatus.live
        entry = await news_cache.get(redis, service.CARD_SOURCE_ID)
        assert entry is not None
        titles = [item.title for item in entry.items]
        # The house line first, the featured product second, then the rest.
        assert titles[0].startswith("outception.ai:")
        assert titles[1].startswith("Star:")
        assert titles[2].startswith("Live one:")
        assert entry.items[1].extra is not None
        assert entry.items[1].extra.hover == "featured"
        assert entry.items[2].extra is not None
        assert entry.items[2].extra.icon is not None
        assert "faviconV2" in entry.items[2].extra.icon
        assert await redis.get(service.CARD_ITEMS_KEY) is not None
        days = await service.archive(session)
        assert [day for day, _ in days] == [today]
        assert [item.name for item in days[0][1]] == ["Star", "Live one"]

    async def test_reject_carries_a_note(
        self, session: AsyncSession, user: User
    ) -> None:
        launch = await service.submit(session, user, _body())
        rejected = await service.reject(
            session, launch.id, "Not a product; mail x@y.io"
        )
        assert rejected.state == LaunchStatus.rejected
        assert rejected.reviewer_note == "Not a product; mail [email]"
        with pytest.raises(BadRequest):
            await service.reject(session, launch.id, "again")

    async def test_edit_is_recorded(
        self, session: AsyncSession, redis: Redis, user: User
    ) -> None:
        launch = await service.submit(session, user, _body())
        edited = await service.edit(
            session,
            redis,
            launch.id,
            LaunchEdit(tagline="Widgets, tidier", kicker="update"),
        )
        assert edited.tagline == "Widgets, tidier"
        assert edited.kicker == "update"
        assert edited.reviewer_note is not None
        assert edited.reviewer_note.startswith("Edited tagline, kicker on ")

    async def test_rotation(
        self, session: AsyncSession, redis: Redis, user: User
    ) -> None:
        today = datetime.now(UTC).date()
        yesterday_launch = await service.submit(session, user, _body("Old"))
        today_launch = await service.submit(session, user, _body("New"))
        await service.approve(
            session,
            redis,
            yesterday_launch.id,
            LaunchApprove(day=today - timedelta(days=1)),
        )
        await service.approve(session, redis, today_launch.id, LaunchApprove(day=today))
        # Simulate the approval having happened before today's rotation.
        yesterday_launch.state = LaunchStatus.live
        today_launch.state = LaunchStatus.approved
        await session.flush()
        counts = await service.rotate_day(session, redis, today)
        assert counts == {"live": 1, "ended": 1}
        assert today_launch.state == LaunchStatus.live
        assert yesterday_launch.state == LaunchStatus.ended
        entry = await news_cache.get(redis, service.CARD_SOURCE_ID)
        assert entry is not None
        # Yesterday's product sits under the fold, after today's.
        assert [item.title.split(":")[0] for item in entry.items] == [
            "outception.ai",
            "New",
            "Old",
        ]


class TestHouseLine:
    def test_house_item_is_always_first_and_never_a_row(self) -> None:
        item = service.house_item(datetime(2026, 10, 4, tzinfo=UTC).date())
        assert item.id == "house-2026-10-04"
        assert item.url == "https://outception.ai"
        assert item.extra is not None
        assert item.extra.hover == "house"


def _png(width: int, height: int) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
class TestLogosAndEdits:
    async def test_a_new_logo_replaces_the_old_and_a_bad_one_keeps_it(
        self,
        session: AsyncSession,
        redis: Redis,
        user: User,
        mocker: MockerFixture,
        tmp_path: object,
    ) -> None:
        mocker.patch.object(settings, "MEDIA_DIR", str(tmp_path))
        fetch = mocker.patch(
            "outception.launches.service.fetch_bytes",
            AsyncMock(return_value=_png(32, 32)),
        )
        launch = await service.submit(
            session, user, _body(logo_url="https://example.com/logo.png")
        )
        assert launch.logo_path is not None
        stored = Path(str(tmp_path)) / launch.logo_path
        first = stored.read_bytes()
        # Not an image: the edit keeps the logo there, untouched.
        fetch.return_value = b"not an image"
        await service.update(
            session,
            redis,
            user,
            launch.id,
            LaunchUpdate.model_validate({"logo_url": "https://example.com/other.png"}),
        )
        assert stored.read_bytes() == first
        # No temporary file is left behind either way.
        assert [p.name for p in stored.parent.iterdir()] == [stored.name]

    def test_a_logo_too_large_to_decode_is_refused(self) -> None:
        assert service._decode_logo(_png(32, 32)) is not None
        assert service._decode_logo(_png(2049, 2048)) is None

    async def test_moving_the_day_alone_tells_the_founder(
        self, session: AsyncSession, redis: Redis, user: User, mocker: MockerFixture
    ) -> None:
        launch = await service.submit(session, user, _body())
        notify = mocker.patch.object(service, "_notify_admins")
        await service.update(session, redis, user, launch.id, LaunchUpdate())
        notify.assert_not_called()
        day = datetime.now(UTC).date() + timedelta(days=9)
        await service.update(
            session, redis, user, launch.id, LaunchUpdate(preferred_day=day)
        )
        notify.assert_called_once()

    def test_race_labels_never_collide(self) -> None:
        assert service.distinct_labels(["Widget", "Widget (2)", "Widget"]) == [
            "Widget",
            "Widget (2)",
            "Widget (3)",
        ]
