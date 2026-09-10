import random
import string
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest_asyncio

from outception.models import (
    OAuthAccount,
    Organization,
    User,
    UserOrganization,
)
from outception.models.organization import STATUS_CAPABILITIES, OrganizationStatus
from outception.models.user import OAuthPlatform
from outception.models.user_organization import OrganizationRole
from tests.fixtures.database import SaveFixture


def rstr(prefix: str) -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def lstr(suffix: str) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6)) + suffix


async def create_organization(
    save_fixture: SaveFixture,
    name_prefix: str = "testorg",
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
    **kwargs: Any,
) -> Organization:
    name = rstr(name_prefix)
    if "created_at" not in kwargs:
        kwargs["created_at"] = datetime(2025, 7, 1, tzinfo=UTC)

    organization = Organization(
        name=name,
        slug=name,
        status=status,
        avatar_url="https://avatars.githubusercontent.com/u/105373340?s=200&v=4",
        **kwargs,
    )
    if "capabilities" not in kwargs:
        organization.capabilities = {**STATUS_CAPABILITIES[status]}
    await save_fixture(organization)
    return organization


@pytest_asyncio.fixture
async def organization(save_fixture: SaveFixture) -> Organization:
    return await create_organization(save_fixture)


@pytest_asyncio.fixture
async def organization_second(save_fixture: SaveFixture) -> Organization:
    return await create_organization(save_fixture)


async def create_oauth_account(
    save_fixture: SaveFixture,
    user: User,
    platform: OAuthPlatform,
) -> OAuthAccount:
    oauth_account = OAuthAccount(
        platform=platform,
        access_token="xxyyzz",
        account_id="xxyyzz",
        account_email="foo@bar.com",
        account_username=rstr("gh_username"),
        user=user,
    )
    await save_fixture(oauth_account)
    return oauth_account


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
        avatar_url="https://avatars.githubusercontent.com/u/47952?v=4",
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


@pytest_asyncio.fixture
async def user_organization(
    save_fixture: SaveFixture,
    organization: Organization,
    user: User,
) -> UserOrganization:
    user_organization = UserOrganization(
        user=user, organization=organization, role=OrganizationRole.owner
    )
    await save_fixture(user_organization)
    return user_organization


@pytest_asyncio.fixture
async def user_organization_second(
    save_fixture: SaveFixture,
    organization: Organization,
    user_second: User,
) -> UserOrganization:
    user_organization = UserOrganization(user=user_second, organization=organization)
    await save_fixture(user_organization)
    return user_organization
