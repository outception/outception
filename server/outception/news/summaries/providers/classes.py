"""Error classes: what a failed model call means for the chain."""

from enum import StrEnum


class ErrorClass(StrEnum):
    refusal = "refusal"  # the model declined: return a safe null, never retry elsewhere
    quota = "quota"  # out of quota: cool the provider down, advance
    auth = "auth"  # a rejected key: disable the lane entry, page
    transient = "transient"  # a timeout or 5xx: cool down briefly, advance
    malformed = "malformed"  # unparsable reply: one repair retry, then advance


class ModelError(Exception):
    """Raised out of the governor and providers. Carries the provider name
    and the class, never the request or a key."""

    def __init__(
        self,
        provider: str,
        error_class: ErrorClass,
        *,
        retry_after: float | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(
            f"{provider}: {error_class}" + (f" ({detail})" if detail else "")
        )
        self.provider = provider
        self.error_class = error_class
        self.retry_after = retry_after
