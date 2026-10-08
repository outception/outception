import re
from collections.abc import AsyncIterator, Sequence

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from ratelimit import Rule

from outception.config import settings
from outception.enums import RateLimitGroup
from outception.rate_limit import (
    _PRODUCTION_RULES,
    _SANDBOX_RULES,
    _authenticate,
    _bearer_token,
    _identity_cache_key,
    _session_cookie,
    clear_cached_identity,
    write_cached_identity,
)
from outception.redis import Redis


@pytest_asyncio.fixture
async def redis() -> AsyncIterator[Redis]:
    yield FakeAsyncRedis(decode_responses=True)


def _http_scope(
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] | None = ("8.8.8.8", 1234),
) -> dict[str, object]:
    return {
        "type": "http",
        "headers": headers or [],
        "client": client,
    }


class TestBearerToken:
    def test_returns_token(self) -> None:
        scope = _http_scope(headers=[(b"authorization", b"Bearer outception_pat_xyz")])
        assert _bearer_token(scope) == "outception_pat_xyz"

    def test_case_insensitive_scheme(self) -> None:
        scope = _http_scope(headers=[(b"authorization", b"BEARER outception_pat_xyz")])
        assert _bearer_token(scope) == "outception_pat_xyz"

    def test_missing_header(self) -> None:
        scope = _http_scope(headers=[])
        assert _bearer_token(scope) is None

    def test_other_scheme(self) -> None:
        scope = _http_scope(headers=[(b"authorization", b"Basic dXNlcjpwYXNz")])
        assert _bearer_token(scope) is None

    def test_empty_token(self) -> None:
        scope = _http_scope(headers=[(b"authorization", b"Bearer ")])
        assert _bearer_token(scope) is None

    def test_non_http_scope(self) -> None:
        scope: dict[str, object] = {"type": "websocket", "headers": []}
        assert _bearer_token(scope) is None


class TestSessionCookie:
    def test_returns_value(self) -> None:
        header = f"{settings.USER_SESSION_COOKIE_KEY}=outception_us_xyz".encode("ascii")
        scope = _http_scope(headers=[(b"cookie", header)])
        assert _session_cookie(scope) == "outception_us_xyz"

    def test_among_other_cookies(self) -> None:
        header = (
            f"foo=bar; {settings.USER_SESSION_COOKIE_KEY}=outception_us_xyz; baz=qux"
        ).encode("ascii")
        scope = _http_scope(headers=[(b"cookie", header)])
        assert _session_cookie(scope) == "outception_us_xyz"

    def test_missing_header(self) -> None:
        scope = _http_scope(headers=[])
        assert _session_cookie(scope) is None

    def test_other_cookies_only(self) -> None:
        scope = _http_scope(headers=[(b"cookie", b"foo=bar; baz=qux")])
        assert _session_cookie(scope) is None

    def test_empty_value(self) -> None:
        header = f"{settings.USER_SESSION_COOKIE_KEY}=".encode("ascii")
        scope = _http_scope(headers=[(b"cookie", header)])
        assert _session_cookie(scope) is None

    def test_non_http_scope(self) -> None:
        scope: dict[str, object] = {"type": "websocket", "headers": []}
        assert _session_cookie(scope) is None


@pytest.mark.asyncio
class TestIdentityCacheRoundTrip:
    async def test_write_then_read_via_authenticate(self, redis: Redis) -> None:
        token = "outception_pat_round_trip"
        await write_cached_identity(
            redis, token, ("user:abc-123", RateLimitGroup.elevated)
        )

        identity = await _authenticate(
            _http_scope(
                headers=[(b"authorization", b"Bearer outception_pat_round_trip")]
            ),
            redis=redis,
        )

        assert identity == ("user:abc-123", RateLimitGroup.elevated)

    async def test_write_sets_ttl(self, redis: Redis) -> None:
        token = "outception_pat_ttl"
        await write_cached_identity(redis, token, ("user:1", RateLimitGroup.default))

        ttl = await redis.ttl(_identity_cache_key(token))
        assert 0 < ttl <= 300

    async def test_clear_removes_entry(self, redis: Redis) -> None:
        token = "outception_pat_clear"
        await write_cached_identity(redis, token, ("user:1", RateLimitGroup.default))
        assert await redis.exists(_identity_cache_key(token)) == 1

        await clear_cached_identity(redis, token)

        assert await redis.exists(_identity_cache_key(token)) == 0


@pytest.mark.asyncio
class TestAuthenticate:
    async def test_unknown_token_is_keyed_on_the_address(self, redis: Redis) -> None:
        identity = await _authenticate(
            _http_scope(
                headers=[(b"authorization", b"Bearer outception_pat_unknown")],
                client=("8.8.8.8", 1234),
            ),
            redis=redis,
        )
        # Keyed on the address: a fresh random token per request must not
        # buy a fresh bucket.
        assert identity == ("8.8.8.8", RateLimitGroup.pending_auth)

    async def test_non_ascii_token_is_keyed_on_the_address(self, redis: Redis) -> None:
        header = "Bearer outception_pat_abc…".encode()
        token = header.decode("latin-1").removeprefix("Bearer ")
        identity = await _authenticate(
            _http_scope(headers=[(b"authorization", header)], client=("8.8.8.8", 1234)),
            redis=redis,
        )
        assert token
        assert identity == ("8.8.8.8", RateLimitGroup.pending_auth)

    async def test_no_token_uses_client_ip(self, redis: Redis) -> None:
        identity = await _authenticate(_http_scope(client=("1.1.1.1", 80)), redis=redis)
        assert identity == ("1.1.1.1", RateLimitGroup.default)

    async def test_rotating_unknown_cookies_share_one_bucket(
        self, redis: Redis
    ) -> None:
        identities = set()
        for n in range(3):
            for name in (
                settings.USER_SESSION_COOKIE_KEY,
                settings.AUTHENTICATION_SESSION_COOKIE_KEY,
            ):
                header = f"{name}=random{n}".encode("ascii")
                identities.add(
                    await _authenticate(
                        _http_scope(
                            headers=[(b"cookie", header)], client=("9.9.9.9", 1)
                        ),
                        redis=redis,
                    )
                )
        assert {identity for identity, _ in identities} == {"9.9.9.9"}

    async def test_no_client_returns_anonymous(self, redis: Redis) -> None:
        identity = await _authenticate(_http_scope(client=None), redis=redis)
        assert identity == ("anonymous", RateLimitGroup.default)

    async def test_cookie_cache_hit(self, redis: Redis) -> None:
        cookie = "outception_us_session"
        await write_cached_identity(redis, cookie, ("user:web", RateLimitGroup.web))

        header = f"{settings.USER_SESSION_COOKIE_KEY}={cookie}".encode("ascii")
        identity = await _authenticate(
            _http_scope(headers=[(b"cookie", header)]), redis=redis
        )

        assert identity == ("user:web", RateLimitGroup.web)

    async def test_unknown_cookie_is_keyed_on_the_address(self, redis: Redis) -> None:
        header = f"{settings.USER_SESSION_COOKIE_KEY}=outception_us_unknown".encode(
            "ascii"
        )
        identity = await _authenticate(
            _http_scope(headers=[(b"cookie", header)], client=("9.9.9.9", 1234)),
            redis=redis,
        )
        assert identity == ("9.9.9.9", RateLimitGroup.pending_auth)

    async def test_bearer_token_preferred_over_cookie(self, redis: Redis) -> None:
        await write_cached_identity(
            redis, "outception_pat_a", ("user:bearer", RateLimitGroup.elevated)
        )
        await write_cached_identity(
            redis, "outception_us_b", ("user:cookie", RateLimitGroup.web)
        )

        cookie_header = f"{settings.USER_SESSION_COOKIE_KEY}=outception_us_b".encode(
            "ascii"
        )
        identity = await _authenticate(
            _http_scope(
                headers=[
                    (b"authorization", b"Bearer outception_pat_a"),
                    (b"cookie", cookie_header),
                ]
            ),
            redis=redis,
        )

        assert identity == ("user:bearer", RateLimitGroup.elevated)

    async def test_distinct_tokens_get_distinct_identities(self, redis: Redis) -> None:
        token_a = "outception_pat_a"
        token_b = "outception_pat_b"
        await write_cached_identity(redis, token_a, ("user:a", RateLimitGroup.default))
        await write_cached_identity(
            redis, token_b, ("organization:b", RateLimitGroup.elevated)
        )

        ident_a = await _authenticate(
            _http_scope(headers=[(b"authorization", b"Bearer outception_pat_a")]),
            redis=redis,
        )
        ident_b = await _authenticate(
            _http_scope(headers=[(b"authorization", b"Bearer outception_pat_b")]),
            redis=redis,
        )

        assert ident_a == ("user:a", RateLimitGroup.default)
        assert ident_b == ("organization:b", RateLimitGroup.elevated)


def _select_rule(
    rules: dict[str, Sequence[Rule]],
    path: str,
    group: RateLimitGroup,
    method: str = "GET",
) -> Rule | None:
    """Mirror the rule selection in ratelimit/core.py."""
    method = method.lower()
    for pattern, pattern_rules in rules.items():
        if not re.compile(pattern).match(path):
            continue
        for rule in pattern_rules:
            if rule.group == group and rule.method.lower() in (method, "*"):
                return rule
    return None


_SENSITIVE_PATHS: list[tuple[str, str]] = [
    ("/v1/login-code/request", "login-code"),
    ("/v1/auth/email-otp/request", "auth-email-otp"),
    ("/v1/auth/totp/verify", "auth-totp"),
    ("/v1/auth/backup-codes/verify", "auth-backup-codes"),
]


@pytest.mark.parametrize("rules", [_PRODUCTION_RULES, _SANDBOX_RULES])
@pytest.mark.parametrize(("path", "expected_zone"), _SENSITIVE_PATHS)
@pytest.mark.parametrize("group", [RateLimitGroup.default, RateLimitGroup.pending_auth])
class TestSensitiveEndpointZoneIsolation:
    """Pending-auth requests (unvalidated bearer/cookie) must use the
    endpoint's own zone, not fall through to the shared "api" zone.

    Regression coverage for https://github.com/outceptionsource/outception/issues/11704.
    """

    def test_resolves_to_endpoint_zone(
        self,
        rules: dict[str, Sequence[Rule]],
        path: str,
        expected_zone: str,
        group: RateLimitGroup,
    ) -> None:
        rule = _select_rule(rules, path, group)
        assert rule is not None, (
            f"No rule selected for path={path!r} group={group.value!r}"
        )
        assert rule.zone == expected_zone, (
            f"Path {path!r} for group {group.value!r} resolved to "
            f"zone {rule.zone!r}, expected {expected_zone!r}"
        )


@pytest.mark.parametrize("rules", [_PRODUCTION_RULES, _SANDBOX_RULES])
@pytest.mark.parametrize("group", [RateLimitGroup.default, RateLimitGroup.web])
class TestLaunchZones:
    """The submit allowance covers submissions and the submitter's edits, and
    nothing else under the prefix: the public view beacon has its own zone,
    and the review actions fall through to the general allowance."""

    def test_submit_and_edit_share_the_zone(
        self, rules: dict[str, Sequence[Rule]], group: RateLimitGroup
    ) -> None:
        submit = _select_rule(rules, "/v1/launches", group, method="POST")
        edit = _select_rule(
            rules, "/v1/launches/0c2a2e5e-3d0d-4a2f-9e55-7a1f5e2c1b11", group, "PATCH"
        )
        assert submit is not None
        assert submit.zone == "launches-submit"
        assert edit is not None
        assert edit.zone == "launches-submit"
        upper = _select_rule(
            rules, "/v1/launches/0C2A1B3D-4E5F-4A6B-8C7D-9E0F1A2B3C4D", group, "PATCH"
        )
        assert upper is not None
        assert upper.zone == "launches-submit"

    def test_beacon_and_review_actions_are_outside_it(
        self, rules: dict[str, Sequence[Rule]], group: RateLimitGroup
    ) -> None:
        beacon = _select_rule(rules, "/v1/launches/views", group, method="POST")
        assert beacon is not None
        assert beacon.zone == "launches-views"
        approve = _select_rule(
            rules,
            "/v1/launches/0c2a2e5e-3d0d-4a2f-9e55-7a1f5e2c1b11/approve",
            group,
            "POST",
        )
        assert approve is not None
        assert approve.zone != "launches-submit"
