from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from outception.app import app as outception_app
from outception.auth.dependencies import _auth_subject_factory_cache
from outception.auth.models import AuthSubject, Subject
from outception.kit.versioning import VERSION_HEADER, APIVersion
from outception.postgres import AsyncSession, get_db_read_session, get_db_session
from outception.redis import Redis, get_redis


class IsolatedSessionTestClient(httpx.AsyncClient):
    """
    Test client that mimics production behavior by clearing session before requests.

    In production, each HTTP request gets a fresh database session. This client
    simulates that by expunging all objects from the test session before each
    request, catching lazy='raise' errors that would otherwise pass in tests.

    Disable for specific tests with @pytest.mark.keep_session_state marker.
    """

    def __init__(
        self, session: AsyncSession, auto_expunge: bool, *args: Any, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self._session = session
        self._auto_expunge = auto_expunge

    async def request(self, *args: Any, **kwargs: Any) -> httpx.Response:
        """Expunge session before each request to simulate production."""
        if self._auto_expunge:
            self._session.expunge_all()
        return await super().request(*args, **kwargs)


@pytest_asyncio.fixture
async def app(
    auth_subject: AuthSubject[Subject], session: AsyncSession, redis: Redis
) -> AsyncGenerator[FastAPI]:
    outception_app.dependency_overrides[get_db_session] = lambda: session
    outception_app.dependency_overrides[get_db_read_session] = lambda: session
    outception_app.dependency_overrides[get_redis] = lambda: redis
    for auth_subject_getter in _auth_subject_factory_cache.values():
        outception_app.dependency_overrides[auth_subject_getter] = lambda: auth_subject

    yield outception_app

    outception_app.dependency_overrides.pop(get_db_session)


@pytest_asyncio.fixture
async def client(
    app: FastAPI,
    session: AsyncSession,
    request: pytest.FixtureRequest,
    api_version: APIVersion | None,
) -> AsyncGenerator[httpx.AsyncClient]:
    # Check if test wants to keep session state (opt-out)
    keep_state = request.node.get_closest_marker("keep_session_state") is not None
    auto_expunge = not keep_state

    async with IsolatedSessionTestClient(
        session=session,
        auto_expunge=auto_expunge,
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={VERSION_HEADER: str(api_version)} if api_version is not None else {},
    ) as client:
        yield client


@pytest.fixture
def api_version(request: pytest.FixtureRequest) -> APIVersion | None:
    return getattr(request, "param", None)


@pytest.hookimpl(specname="pytest_generate_tests")
def pytest_generate_tests_api_version(metafunc: pytest.Metafunc) -> None:
    if "api_version" not in metafunc.fixturenames:
        return
    marker = metafunc.definition.get_closest_marker("api_version")
    if marker is None:
        return
    if not marker.args or any(not isinstance(arg, APIVersion) for arg in marker.args):
        raise ValueError("api_version marker requires one or more APIVersion arguments")
    metafunc.parametrize("api_version", marker.args, indirect=True, ids=str)
