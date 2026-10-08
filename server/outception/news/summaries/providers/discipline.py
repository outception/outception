"""How an HTTP failure from a model endpoint is read: what class it is for
the chain, how long the key that hit it sits on the bench, and whether the
key itself was rejected. Two readings exist because the endpoints speak
differently: one puts its markers in the body text, the others in
structured error fields (and sometimes echo request content into
validation messages, so a paywalled article containing "payment required"
must not bench a healthy key)."""

import json
import re
from dataclasses import dataclass

import httpx

from .classes import ErrorClass
from .pool import seconds_until_reset

MAX_COOLDOWN_SECONDS = 60 * 60
BURST_COOLDOWN_SECONDS = 30
OUTAGE_COOLDOWN_SECONDS = 60
# One slow answer is usually one slow answer, not an outage.
TIMEOUT_COOLDOWN_SECONDS = 10


@dataclass(frozen=True)
class Discipline:
    reset_hour_utc: int
    dead_markers: tuple[str, ...]
    # Read the markers off the body text (True) or the structured error
    # code and type fields only (False).
    markers_in_body: bool
    # Statuses that reject the key whatever the body says.
    always_dead: tuple[int, ...] = ()
    daily_pattern: str = r"per day|daily|RPD|TPD"

    def rejects_key(self, exc: BaseException) -> bool:
        if not isinstance(exc, httpx.HTTPStatusError):
            return False
        status = exc.response.status_code
        if status in self.always_dead:
            return True
        if status not in (400, 401, 403):
            return False
        if self.markers_in_body:
            body = exc.response.text[:4000].lower()
            return any(marker in body for marker in self.dead_markers)
        try:
            error = exc.response.json().get("error") or {}
        except ValueError, AttributeError:
            return False
        if not isinstance(error, dict):
            return False
        fields = " ".join(
            str(error.get(name) or "") for name in ("code", "type")
        ).lower()
        return any(marker in fields for marker in self.dead_markers)

    def cooldown_seconds(self, exc: BaseException) -> int | None:
        """How long to bench the key; None when the failure says nothing
        about capacity (an empty or unparsable reply) and the next call may
        retry."""
        if isinstance(exc, httpx.HTTPStatusError):
            if self.rejects_key(exc):
                return MAX_COOLDOWN_SECONDS
            if exc.response.status_code == 429:
                body = exc.response.text[:4000]
                retry_after = exc.response.headers.get("retry-after")
                if retry_after and retry_after.isdigit():
                    return max(5, min(MAX_COOLDOWN_SECONDS, int(retry_after)))
                if re.search(self.daily_pattern, body, re.IGNORECASE):
                    return max(
                        BURST_COOLDOWN_SECONDS,
                        min(
                            MAX_COOLDOWN_SECONDS,
                            seconds_until_reset(self.reset_hour_utc),
                        ),
                    )
                match = re.search(r'"retryDelay":\s*"(\d+)(?:\.\d+)?s"', body)
                if match:
                    return max(5, min(MAX_COOLDOWN_SECONDS, int(match.group(1))))
                return BURST_COOLDOWN_SECONDS
            return OUTAGE_COOLDOWN_SECONDS
        if isinstance(exc, httpx.TimeoutException):
            return TIMEOUT_COOLDOWN_SECONDS
        if isinstance(exc, httpx.HTTPError | httpx.StreamError):
            return OUTAGE_COOLDOWN_SECONDS
        return None

    def classify(self, exc: BaseException) -> ErrorClass:
        if isinstance(exc, httpx.HTTPStatusError):
            if self.rejects_key(exc):
                return ErrorClass.auth
            status = exc.response.status_code
            if status == 429:
                return ErrorClass.quota
            if status >= 500:
                return ErrorClass.transient
            return ErrorClass.transient
        if isinstance(exc, httpx.HTTPError | httpx.StreamError | TimeoutError):
            return ErrorClass.transient
        if isinstance(exc, ValueError | json.JSONDecodeError):
            return ErrorClass.malformed
        return ErrorClass.transient


# The free-tier daily quotas of the first-line provider reset at midnight
# Pacific (07:00 or 08:00 UTC); its rejections are worded in the body.
FIRST_LINE = Discipline(
    reset_hour_utc=8,
    dead_markers=(
        "api_key_invalid",
        "api key not valid",
        "consumer_suspended",
        "permission_denied",
        "service_disabled",
        "has been suspended",
    ),
    markers_in_body=True,
    daily_pattern=r"PerDay|per day|daily",
)

# The OpenAI-style endpoints: structured error fields, 401 and 402 speak
# for themselves (the key or the account behind it is the problem), and
# daily quotas roll on their own clocks, so an hourly re-probe is the
# compromise.
OPENAI_STYLE = Discipline(
    reset_hour_utc=0,
    dead_markers=(
        "invalid_api_key",
        "invalid api key",
        "api key not valid",
        "account_deactivated",
        "permission_denied",
    ),
    markers_in_body=False,
    always_dead=(401, 402),
)
