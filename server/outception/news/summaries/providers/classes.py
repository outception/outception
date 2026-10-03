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

    # Whether the chain should cool the whole provider down (or disable it)
    # on this error; a pool-level failure handles its own key instead.
    cool_provider: bool = True


class KeyBenched(ModelError):
    """One key of a provider's pool failed and was benched by the pool; the
    pool may still hold others, so the chain advances without cooling the
    provider down or disabling it."""

    cool_provider = False

    def __init__(
        self, provider: str, error_class: ErrorClass, *, key_index: int
    ) -> None:
        super().__init__(provider, error_class, detail=f"key {key_index} benched")
        self.key_index = key_index


class PoolExhausted(ModelError):
    """Every key of the pool is benched or minute-full right now: advance,
    and keep the provider out of the chain briefly so the next calls in the
    same minute do not probe it again."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            provider, ErrorClass.quota, retry_after=15.0, detail="pool exhausted"
        )
