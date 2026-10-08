"""Hero-summary warming queues. The first tap on an article generates its
summary live, which reads as slow. Readers overwhelmingly tap the hero
headline, so serving a card queues that one URL for background
pre-summarization. Strictly free: the warmer runs on the background lane,
which never reaches the paid provider, has its own daily cap, and stands
down once live taps have consumed half the global budget."""

from outception.redis import Redis
from outception.worker import enqueue_job

from .extract import is_unsummarizable
from .providers.registry import free_configured

WARM_QUEUE_KEY = "news:summary:warm"
# Handoffs from live taps: a reader has already waited for this article and
# been sent to it without a summary, so it jumps the hero queue.
WARM_URGENT_KEY = "news:summary:warm:urgent"
# Speculative candidates: heroes of cards nobody has opened yet, drained
# only after the viewed-card queue is empty.
WARM_PRETAP_KEY = "news:summary:warm:pretap"
# Debounces the urgent warmer kick: during a provider brownout every failed
# tap becomes a handoff, and each one was its own broker message.
WARM_KICK_KEY = "news:summary:warm:kick"
WARM_QUEUE_TTL_SECONDS = 6 * 60 * 60
WARM_QUEUE_MAX = 500
WARM_URGENT_MAX = 200

_ORIGIN_KEYS = {
    "urgent": WARM_URGENT_KEY,
    "viewed": WARM_QUEUE_KEY,
    "pretap": WARM_PRETAP_KEY,
}


def _acceptable(url: str) -> bool:
    return url.startswith(("http://", "https://")) and not is_unsummarizable(url)


async def note_warm_candidate(
    redis: Redis, url: str, lang: str, *, urgent: bool = False
) -> None:
    """Queue a hero headline for pre-summarization. One cheap SADD on the
    serving path; all real checks happen in the warmer task. `urgent`
    queues a live tap's handoff instead: FIFO, drained first, admitted
    regardless of the hero queue's size."""
    if urgent:
        if not free_configured() or not _acceptable(url):
            return
        pipe = redis.pipeline()
        pipe.lpush(WARM_URGENT_KEY, f"{lang}\t{url}")
        pipe.ltrim(WARM_URGENT_KEY, 0, WARM_URGENT_MAX - 1)
        pipe.expire(WARM_URGENT_KEY, WARM_QUEUE_TTL_SECONDS)
        pipe.set(WARM_KICK_KEY, "1", ex=30, nx=True)
        results = await pipe.execute()
        # Kick the warmer now rather than leaving the handoff to the cron,
        # NX-debounced. The job queue is request-bound, absent in bare
        # scripts and tests: a missing manager just means the cron picks the
        # handoff up as before.
        if results[-1]:
            try:
                enqueue_job("news.warm_summaries")
            except RuntimeError:
                pass
        return
    await note_warm_candidates(redis, [url], lang)


async def note_warm_candidates(
    redis: Redis, urls: list[str], lang: str, *, pretap: bool = False
) -> None:
    """Queue several hero headlines at once: one SCARD and one pipeline for
    the whole batch. `pretap` routes speculative candidates to their own
    second-class queue."""
    if not free_configured():
        return
    payloads = [f"{lang}\t{url}" for url in urls if _acceptable(url)]
    if not payloads:
        return
    queue_key = WARM_PRETAP_KEY if pretap else WARM_QUEUE_KEY
    if await redis.scard(queue_key) >= WARM_QUEUE_MAX:
        return
    pipe = redis.pipeline()
    pipe.sadd(queue_key, *payloads)
    pipe.expire(queue_key, WARM_QUEUE_TTL_SECONDS)
    await pipe.execute()


async def requeue_warm_candidate(
    redis: Redis, url: str, lang: str, *, origin: str
) -> None:
    """Put a popped candidate back where it came from: the warmer draws it
    again when providers recover. RPUSH for the urgent FIFO (pop reads from
    the right, so this really is back on top), and the TTL is refreshed so
    a queue kept alive only by requeues cannot expire mid-brownout."""
    key = _ORIGIN_KEYS.get(origin, WARM_QUEUE_KEY)
    pipe = redis.pipeline()
    if origin == "urgent":
        pipe.rpush(key, f"{lang}\t{url}")
    else:
        pipe.sadd(key, f"{lang}\t{url}")
    pipe.expire(key, WARM_QUEUE_TTL_SECONDS)
    await pipe.execute()


async def pop_warm_candidate(redis: Redis) -> tuple[str, str, str] | None:
    """Next (url, lang, origin) from the warm queues, or None when they are
    drained. Live-tap handoffs first (oldest first), then heroes of viewed
    cards, and the speculative queue only when both are empty. Malformed
    entries are consumed and skipped rather than ending the run."""
    for _ in range(50):
        origin = "urgent"
        raw = await redis.rpop(WARM_URGENT_KEY)
        if raw is None:
            origin = "viewed"
            raw = await redis.spop(WARM_QUEUE_KEY)
        if raw is None:
            origin = "pretap"
            raw = await redis.spop(WARM_PRETAP_KEY)
        if raw is None:
            return None
        entry = raw.decode() if isinstance(raw, bytes) else str(raw)
        lang, sep, url = entry.partition("\t")
        if sep:
            return url, lang, origin
    return None
