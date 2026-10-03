"""MinHash over word shingles of a headline and teaser, with banding so
candidates come from a bucket lookup and never from a scan. The
permutations are fixed by seed, so a signature stored today still
compares tomorrow."""

import base64
import hashlib
import random
import re
import struct

NUM_PERM = 64
BANDS = 16
ROWS = NUM_PERM // BANDS
SHINGLE = 3
_PRIME = (1 << 61) - 1
_MAX_HASH = (1 << 32) - 1

_rng = random.Random(20261003)
_A = [_rng.randrange(1, _PRIME) for _ in range(NUM_PERM)]
_B = [_rng.randrange(0, _PRIME) for _ in range(NUM_PERM)]

_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "by",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "he",
        "she",
        "they",
        "we",
        "you",
        "his",
        "her",
        "their",
        "our",
        "your",
        "i",
        "after",
        "before",
        "over",
        "under",
        "into",
        "onto",
        "about",
        "says",
        "said",
        "say",
        "will",
        "would",
        "can",
        "could",
    ]
)


def tokens(text: str) -> list[str]:
    return [
        t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1
    ]


def shingles(text: str, k: int = SHINGLE) -> set[str]:
    words = tokens(text)
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def _hash(shingle: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(shingle.encode(), digest_size=4).digest(), "big"
    )


def signature(text: str) -> list[int]:
    grams = shingles(text)
    if not grams:
        return [_MAX_HASH] * NUM_PERM
    hashes = [_hash(g) for g in grams]
    return [
        min(((a * h + b) % _PRIME) & _MAX_HASH for h in hashes)
        for a, b in zip(_A, _B, strict=True)
    ]


def estimate(a: list[int], b: list[int]) -> float:
    """The Jaccard estimate: the share of agreeing minimums."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(1 for x, y in zip(a, b, strict=True) if x == y) / len(a)


def band_keys(sig: list[int]) -> list[str]:
    keys: list[str] = []
    for band in range(BANDS):
        rows = sig[band * ROWS : (band + 1) * ROWS]
        digest = hashlib.blake2b(
            struct.pack(f">{ROWS}I", *rows), digest_size=6
        ).hexdigest()
        keys.append(f"{band}:{digest}")
    return keys


def encode(sig: list[int]) -> str:
    return base64.b64encode(struct.pack(f">{len(sig)}I", *sig)).decode()


def decode(raw: str | bytes) -> list[int]:
    data = base64.b64decode(raw)
    return list(struct.unpack(f">{len(data) // 4}I", data))
