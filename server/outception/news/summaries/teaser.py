"""The publisher's own standfirst, cleaned: error pages and bot walls leak
into feed descriptions and meta tags when a publisher's pipeline hiccups,
and a card once presented a rate-limit error as the publisher's summary.
Shapes of machine noise only; topical words stay allowed, because a real
standfirst may legitimately contain them."""

import re

TEASER_MIN_CHARS = 40
TEASER_MAX_CHARS = 400

TEASER_JUNK = re.compile(
    r"(?i)(?:^\s*warning:|(?:error|http|status)\s*\d{3}"
    # "Too many requests" also occurs in ordinary prose, so it counts as
    # junk only next to a status code or an error or blocked word, which is
    # how a machine writes it.
    r"|(?:\b\d{3}\b|error|blocked|denied)[^.]{0,24}?too many requests"
    r"|too many requests[^.]{0,24}?(?:\b\d{3}\b|error|blocked|denied)"
    r"|access denied|enable (?:javascript|cookies)|are you a robot"
    r"|attention required|request blocked|verify you are human|captcha"
    # The CDN 403 bodies, which say none of the above. "...to access/view"
    # only: a council story about residents who "do not have permission to
    # park" is ordinary prose, not a blocked fetch.
    r"|(?:do(?:es)?n'?t|do(?:es)? not) have permission to (?:access|view)"
    r"|not authorized to (?:view|access)"
    r"|reference\s*#\s*[0-9a-f][0-9a-f.]{6,}"
    r"|errors\.edgesuite\.net"
    r"|request could not be satisfied"
    r"|access to this page has been denied"
    r"|your request has been blocked)"
)


def clean_teaser(text: str | None) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) < TEASER_MIN_CHARS:
        return None
    if TEASER_JUNK.search(text):
        return None
    if len(text) > TEASER_MAX_CHARS:
        cut = text.rfind(" ", 0, TEASER_MAX_CHARS)
        text = text[: cut if cut > TEASER_MIN_CHARS else TEASER_MAX_CHARS] + "…"
    return text
