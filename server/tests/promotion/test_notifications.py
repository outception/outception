import pytest

from polar.models import User
from polar.postgres import AsyncSession
from polar.promotion.notifications import build_email
from polar.promotion.service import promotion as promotion_service


async def _make_pending(
    session: AsyncSession, user: User, *, blocks: int = 2
) -> object:
    return await promotion_service.create_pending(
        session,
        author_id=user.id,
        category="tech",
        title="Buy our widget",
        body="World",
        link="https://example.com",
        image_url=None,
        blocks=blocks,
    )


@pytest.mark.asyncio
class TestBuildEmail:
    async def test_activated_email(self, session: AsyncSession, user: User) -> None:
        promotion = await _make_pending(session, user, blocks=3)
        subject, html = build_email(promotion, "activated")
        assert "is live" in subject
        assert "Buy our widget" in subject
        assert "tech" in html
        assert "30 minutes" in html  # 3 blocks × 10 min
        assert "View your promotions" in html

    async def test_queued_email(self, session: AsyncSession, user: User) -> None:
        promotion = await _make_pending(session, user)
        subject, html = build_email(promotion, "queued")
        assert "queued" in subject
        assert "Buy our widget" in subject
        assert "tech" in html
        assert "in line" not in html  # no position given

    async def test_queued_email_with_position(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        _subject, html = build_email(promotion, "queued", position=3)
        assert "#3" in html
        assert "in line" in html

    async def test_expired_email_includes_stats(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        promotion.impressions = 42
        promotion.clicks = 7
        subject, html = build_email(promotion, "expired")
        assert "has ended" in subject
        assert "42" in html
        assert "7" in html

    @pytest.mark.parametrize("kind", ["activated", "queued", "expired"])
    async def test_title_is_html_escaped(
        self, session: AsyncSession, user: User, kind: str
    ) -> None:
        # Every branch interpolates the title into the HTML body, so each must
        # escape it — guards against a future branch using the raw title.
        promotion = await _make_pending(session, user)
        promotion.title = "<script>alert(1)</script>"
        _subject, html = build_email(promotion, kind)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
