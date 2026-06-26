from typing import Any, Literal

import pytest

from outception.auth.models import Anonymous, AuthSubject, Subject
from outception.auth.scope import Scope
from outception.models import Organization, User


class AuthSubjectFixture:
    def __init__(
        self,
        *,
        subject: Literal[
            "anonymous",
            "user",
            "user_second",
            "organization",
            "organization_second",
            "customer",
            "member_owner",
            "member_billing_manager",
            "member",
        ] = "user",
        scopes: set[Scope] = set(Scope),
    ):
        self.subject = subject
        self.scopes = scopes

    def __repr__(self) -> str:
        scopes = (
            "{" + ", ".join(repr(scope.value) for scope in sorted(self.scopes)) + "}"
        )
        return f"AuthSubjectFixture(subject={self.subject!r}, scopes={scopes})"


@pytest.fixture
def auth_subject(
    request: pytest.FixtureRequest,
    user: User,
    user_second: User,
    organization: Organization,
    organization_second: Organization,
) -> AuthSubject[Subject]:
    """
    This fixture generates an AuthSubject instance used by the `client` fixture
    to override the FastAPI authentication dependency, but also can be used manually
    if needed.

    Its parameters are generated through the `auth` marker.
    See `pytest_generate_tests` below for more information.
    """
    auth_subject_fixture: AuthSubjectFixture = request.param

    subjects_map: dict[str, Anonymous | User | Organization] = {
        "anonymous": Anonymous(),
        "user": user,
        "user_second": user_second,
        "organization": organization,
        "organization_second": organization_second,
    }

    subject_key = auth_subject_fixture.subject
    subject = subjects_map[subject_key]

    # For User subjects, provide a mock UserSession so is_web_session() returns True.
    # This matches real web session behavior where all User sessions are UserSessions.
    session: Any = None
    if isinstance(subject, User):
        from unittest.mock import MagicMock

        from outception.models import UserSession

        session = MagicMock(spec=UserSession)

    return AuthSubject(subject, auth_subject_fixture.scopes, session)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # The test requests the `auth_subject` fixture
    if "auth_subject" in metafunc.fixturenames:
        pytest_params = []

        # The test is decorated with the `auth` marker
        auth_marker = metafunc.definition.get_closest_marker("auth")
        if auth_marker is not None:
            # No argument: use a default AuthSubjectFixture
            args: tuple[Any] = auth_marker.args
            if len(args) == 0:
                args = (AuthSubjectFixture(),)

            # Generate a test for each AuthSubjectFixture argument
            for arg in args:
                if not isinstance(arg, AuthSubjectFixture):
                    raise ValueError(
                        "auth marker arguments must be "
                        f"of type AuthSubjectFixture, got {type(arg)}"
                    )
                pytest_params.append(pytest.param(arg, id=repr(arg)))
        # Test is not decorated with `auth` marker: consider the user anonymous
        else:
            pytest_params = [
                pytest.param(AuthSubjectFixture(subject="anonymous"), id="anonymous")
            ]
        metafunc.parametrize("auth_subject", pytest_params, indirect=["auth_subject"])
