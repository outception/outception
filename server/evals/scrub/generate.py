"""Generated valid identifiers per class, for the recall check."""

import random


def _luhn_complete(prefix: str) -> str:
    digits = [int(d) for d in prefix]
    total = 0
    for index, digit in enumerate(reversed(digits)):
        n = digit * 2 if index % 2 == 0 else digit
        total += n - 9 if n > 9 else n
    return prefix + str((10 - total % 10) % 10)


def _ppsn(rng: random.Random) -> str:
    digits = "".join(str(rng.randrange(10)) for _ in range(7))
    total = sum(int(d) * w for d, w in zip(digits, range(8, 1, -1), strict=True))
    return digits + "WABCDEFGHIJKLMNOPQRSTUV"[total % 23]


def generated(seed: int = 7, n: int = 100) -> dict[str, list[str]]:
    rng = random.Random(seed)
    emails = [
        f"user{rng.randrange(10**6)}@example{rng.randrange(100)}.org" for _ in range(n)
    ]
    phones = [
        f"+{rng.randrange(1, 99)} {rng.randrange(10, 999)} {rng.randrange(100, 999)} {rng.randrange(1000, 9999)}"
        for _ in range(n)
    ]
    secrets = [
        "sk-"
        + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(32))
        for _ in range(n)
    ]
    cards = [
        _luhn_complete("4" + "".join(str(rng.randrange(10)) for _ in range(14)))
        for _ in range(n)
    ]
    cards = [f"{c[:4]} {c[4:8]} {c[8:12]} {c[12:]}" for c in cards]
    ids = [_ppsn(rng) for _ in range(n)]
    addresses = [
        f"the server at {rng.randrange(1, 223)}.{rng.randrange(256)}.{rng.randrange(256)}.{rng.randrange(1, 255)}"
        for _ in range(n)
    ]
    return {
        "email": emails,
        "phone": phones,
        "secret": secrets,
        "card": cards,
        "id": ids,
        "address": addresses,
    }
