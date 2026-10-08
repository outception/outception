import secrets
import string
import uuid
from datetime import datetime

import pytest_asyncio

from outception.enums import EmailSender
from outception.models import EmailLog, User
from outception.models.email_log import EmailLogStatus
from outception.models.user import OAuthAccount, OAuthPlatform
from tests.fixtures.database import SaveFixture


def rstr(prefix: str) -> str:
    return prefix + "".join(secrets.choice(string.ascii_letters) for _ in range(6))


def lstr(suffix: str) -> str:
    return "".join(secrets.choice(string.ascii_letters) for _ in range(6)) + suffix


async def create_oauth_account(
    save_fixture: SaveFixture,
    user: User,
    platform: OAuthPlatform,
) -> OAuthAccount:
    oauth_account = OAuthAccount(
        platform=platform,
        account_id="xxyyzz",
        account_email="foo@bar.com",
        account_username=rstr("username"),
        user=user,
    )
    await oauth_account.set_tokens(access_token="xxyyzz", refresh_token=None)
    await save_fixture(oauth_account)
    return oauth_account


async def create_user_google_oauth(
    save_fixture: SaveFixture,
    user: User,
) -> OAuthAccount:
    return await create_oauth_account(save_fixture, user, OAuthPlatform.google)


@pytest_asyncio.fixture
async def user_google_oauth(
    save_fixture: SaveFixture,
    user: User,
) -> OAuthAccount:
    return await create_user_google_oauth(save_fixture, user)


async def create_user_microsoft_oauth(
    save_fixture: SaveFixture,
    user: User,
) -> OAuthAccount:
    return await create_oauth_account(save_fixture, user, OAuthPlatform.microsoft)


@pytest_asyncio.fixture
async def user_microsoft_oauth(
    save_fixture: SaveFixture,
    user: User,
) -> OAuthAccount:
    return await create_user_microsoft_oauth(save_fixture, user)


async def create_user(
    save_fixture: SaveFixture,
    email_verified: bool = True,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=rstr("test") + "@example.com",
        email_verified=email_verified,
        avatar_url="https://example.com/avatar.png",
        oauth_accounts=[],
    )
    await save_fixture(user)
    return user


@pytest_asyncio.fixture
async def user(save_fixture: SaveFixture) -> User:
    return await create_user(save_fixture)


@pytest_asyncio.fixture
async def user_second(save_fixture: SaveFixture) -> User:
    return await create_user(save_fixture)


async def create_email_log(
    save_fixture: SaveFixture,
    *,
    created_at: datetime,
    status: EmailLogStatus = EmailLogStatus.sent,
) -> EmailLog:
    email_log = EmailLog(
        created_at=created_at,
        status=status,
        processor=EmailSender.smtp,
        to_email_addr="reader@example.com",
        from_email_addr="no-reply@example.com",
        from_name="Outception",
        subject="Sign in",
        email_props={},
    )
    await save_fixture(email_log)
    return email_log
