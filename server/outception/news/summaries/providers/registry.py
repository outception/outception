"""The providers built from settings, and the chains over them. A
provider with no key is simply not in the pool; nothing else changes.
Vendor identifiers live here and in the governor's key table, nowhere
else."""

from outception.config import settings
from outception.redis import Redis

from .base import Decider, Provider
from .chain import Chains
from .gemini import GeminiProvider
from .governor import PAID_PROVIDERS, Governor, keys_for
from .llm_decider import LLMDecider
from .openai_compatible import OpenAICompatible
from .own import OwnModel
from .paid import PaidProvider
from .pool import KeyPool

# id -> (url, model setting, rpm setting, rpd setting)
_OPENAI_STYLE: dict[str, tuple[str, str, str, str | None]] = {
    "groq": (
        "https://api.groq.com/openai/v1/chat/completions",
        "GROQ_MODEL",
        "GROQ_RPM_CAP",
        None,
    ),
    "mistral": (
        "https://api.mistral.ai/v1/chat/completions",
        "MISTRAL_MODEL",
        "MISTRAL_RPM_CAP",
        None,
    ),
    "nvidia": (
        "https://integrate.api.nvidia.com/v1/chat/completions",
        "NVIDIA_MODEL",
        "NVIDIA_RPM_CAP",
        None,
    ),
    "ollama": (
        "https://ollama.com/v1/chat/completions",
        "OLLAMA_MODEL",
        "OLLAMA_RPM_CAP",
        None,
    ),
    "cloudflare": (
        "https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions",
        "CLOUDFLARE_MODEL",
        "CLOUDFLARE_RPM_CAP",
        "CLOUDFLARE_DAILY_CAP",
    ),
}

FREE_PROVIDERS = ("gemini", *_OPENAI_STYLE)


def _openai_style(redis: Redis, provider_id: str) -> Provider | None:
    url, model_field, rpm_field, rpd_field = _OPENAI_STYLE[provider_id]
    keys = keys_for(provider_id)
    if not keys:
        return None
    if provider_id == "cloudflare":
        # The endpoint is per account: a token alone cannot build a URL.
        if not settings.CLOUDFLARE_ACCOUNT_ID:
            return None
        url = url.format(account=settings.CLOUDFLARE_ACCOUNT_ID)
    pool = KeyPool(
        redis,
        provider_id,
        keys,
        rpm=int(getattr(settings, rpm_field)),
        rpd=int(getattr(settings, rpd_field)) if rpd_field else 0,
    )
    return OpenAICompatible(
        provider_id, url=url, model=str(getattr(settings, model_field)), pool=pool
    )


def build_providers(redis: Redis) -> dict[str, Provider]:
    providers: dict[str, Provider] = {}
    gemini_keys = keys_for("gemini")
    if gemini_keys:
        providers["gemini"] = GeminiProvider(
            KeyPool(
                redis,
                "gemini",
                gemini_keys,
                rpm=settings.GEMINI_RPM_CAP,
                reset_hour_utc=8,
            )
        )
    for provider_id in _OPENAI_STYLE:
        provider = _openai_style(redis, provider_id)
        if provider is not None:
            providers[provider_id] = provider
    paid_keys = keys_for("paid")
    if paid_keys:
        providers["paid"] = PaidProvider(KeyPool(redis, "paid", paid_keys))
    if settings.OWN_GENERATION_URL:
        providers["own"] = OpenAICompatible(
            "own",
            url=settings.OWN_GENERATION_URL,
            model=settings.OWN_GENERATION_MODEL or "own",
            pool=KeyPool(redis, "own", [settings.OWN_GENERATION_API_KEY or "none"]),
        )
    return providers


def build_deciders(providers: dict[str, Provider]) -> dict[str, Decider]:
    deciders: dict[str, Decider] = {}
    own = OwnModel(key=settings.ENGINE_API_KEY)
    if own.configured:
        deciders["own"] = own
    # The LLM decider renders onto the first free provider that exists; the
    # chain walks providers through the governor as it does for prose.
    for provider_id in FREE_PROVIDERS:
        provider = providers.get(provider_id)
        if provider is not None:
            deciders["llm_decider"] = LLMDecider(provider)
            break
    return deciders


def build_chains(redis: Redis) -> Chains:
    providers = build_providers(redis)
    return Chains(Governor(redis), providers, build_deciders(providers))


def free_configured() -> bool:
    """Whether any free (background-eligible) provider has a key: what the
    warm queues need before they accept a candidate."""
    if any(
        keys_for(provider_id)
        for provider_id in FREE_PROVIDERS
        if provider_id != "cloudflare"
    ):
        return True
    return bool(keys_for("cloudflare") and settings.CLOUDFLARE_ACCOUNT_ID)


def any_configured() -> bool:
    return (
        free_configured()
        or any(keys_for(provider_id) for provider_id in PAID_PROVIDERS)
        or bool(settings.OWN_GENERATION_URL)
    )
