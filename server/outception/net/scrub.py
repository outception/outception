"""Redaction before anything a model or an operator wrote is published:
emails, phone numbers, keys and tokens, card numbers, national ids and
addressed IPs become bracketed placeholders. Never run on headlines or
source names: those are the publishers' words and link out.

A keyword and prefix prefilter runs first so the cost on a summary is
negligible; the patterns only run on text that could hold a hit.
`SCRUB_VERSION` is recorded beside cached text so it can be re-scrubbed
lazily when the rules change."""

import re
from dataclasses import dataclass, field

SCRUB_VERSION = 1

EMAIL = "[email]"
PHONE = "[phone]"
SECRET = "[secret]"
CARD = "[card]"
NATIONAL_ID = "[id]"
ADDRESS = "[address]"

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Separators or a country code are required: never a bare run of digits.
_PHONE_RE = re.compile(
    r"(?<!\d\s)(?<!\d-)(?<!\d\.)(?<![\w.])"
    r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?|\d{1,4}[\s.-])\d{3,4}[\s.-]\d{3,4}"
    r"(?![\s.-]?\d)(?![\w.])"
)
_SECRET_RE = re.compile(
    r"(?:"
    r"\bsk-[A-Za-z0-9_-]{16,}"  # model keys
    r"|\bghp_[A-Za-z0-9]{20,}"  # code hosting tokens
    r"|\bxox[abpr]-[A-Za-z0-9-]{10,}"  # chat tokens
    r"|\bAKIA[A-Z0-9]{16}\b"  # cloud access keys
    r"|\bAIza[A-Za-z0-9_-]{30,}"  # API keys
    r"|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"  # JWT shape
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    r"|\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?|amqp)://[^\s:@/]+:[^\s@/]+@[^\s]+"
    r")"
)
_CARD_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
_IP_KEYWORDS = re.compile(r"\b(?:ip|host|server|address|addr)\b", re.IGNORECASE)
# National ids with a known shape and, where one exists, a checksum: the
# Irish PPS number (letter checksum), the UK national insurance number
# (shape only, no checksum is published), the US social security number
# (shape only).
_PPSN_RE = re.compile(r"\b(\d{7})([A-W])([A-IW]?)\b")
_NINO_RE = re.compile(
    r"\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"
)
_SSN_RE = re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")

# Only text that could hold a hit reaches the patterns.
_PREFILTER = re.compile(
    r"@|\+?\d[\d\s().-]{6,}\d|sk-|ghp_|xox[abpr]-|AKIA|AIza|eyJ|PRIVATE KEY|://"
    r"|\d{7}[A-W]|\d{3}-\d{2}-\d{4}|[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}"
    r"|\b(?:ip|host|server|addr)\b",
    re.IGNORECASE,
)


def luhn_ok(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        n = int(char)
        if index % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def ppsn_ok(match: re.Match[str]) -> bool:
    """The Irish personal public service number: seven digits, a check
    letter, an optional second letter folded into the sum."""
    digits, check, second = match.group(1), match.group(2), match.group(3)
    total = sum(
        int(d) * weight for d, weight in zip(digits, range(8, 1, -1), strict=True)
    )
    if second:
        total += (ord(second) - ord("A") + 1) * 9 if second != "W" else 0
    return "WABCDEFGHIJKLMNOPQRSTUV"[total % 23] == check


@dataclass
class ScrubResult:
    text: str
    hits: dict[str, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return bool(self.hits)


def _count(result: ScrubResult, label: str, n: int) -> None:
    if n:
        result.hits[label] = result.hits.get(label, 0) + n


def scrub_report(text: str) -> ScrubResult:
    result = ScrubResult(text)
    if not text or _PREFILTER.search(text) is None:
        return result
    out = text
    out, n = _SECRET_RE.subn(SECRET, out)
    _count(result, "secret", n)
    out, n = _EMAIL_RE.subn(EMAIL, out)
    _count(result, "email", n)

    def card(match: re.Match[str]) -> str:
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            return CARD
        return match.group(0)

    before = out.count(CARD)
    out = _CARD_RE.sub(card, out)
    _count(result, "card", out.count(CARD) - before)
    out, n = _PHONE_RE.subn(PHONE, out)
    _count(result, "phone", n)
    before = out.count(NATIONAL_ID)
    out = _PPSN_RE.sub(lambda m: NATIONAL_ID if ppsn_ok(m) else m.group(0), out)
    out = _NINO_RE.sub(NATIONAL_ID, out)
    out = _SSN_RE.sub(NATIONAL_ID, out)
    _count(result, "id", out.count(NATIONAL_ID) - before)

    def address(match: re.Match[str]) -> str:
        start = max(0, match.start() - 48)
        if _IP_KEYWORDS.search(out[start : match.start()]):
            return ADDRESS
        return match.group(0)

    before = out.count(ADDRESS)
    out = _IPV4_RE.sub(address, out)
    _count(result, "address", out.count(ADDRESS) - before)
    result.text = out
    return result


def scrub(text: str) -> str:
    return scrub_report(text).text
