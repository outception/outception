"""The canonical key of a link: the same article under tracking
parameters, mobile and AMP mirrors, fragments and trailing slashes keys
the same. Also what the feed parser dedupes on."""

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "piwik_", "matomo_", "hsa_", "vero_")
TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "gbraid",
        "wbraid",
        "msclkid",
        "yclid",
        "igshid",
        "mkt_tok",
        "ref",
        "ref_src",
        "refsrc",
        "cmpid",
        "ncid",
        "ocid",
        "spm",
        "s",
        "sr_share",
        "share",
        "source",
        "src",
        "ito",
        "ns_mchannel",
        "ns_source",
        "ns_campaign",
        "ns_linkname",
        "at_medium",
        "at_campaign",
        "xtor",
        "_ga",
        "_gl",
        "feature",
    }
)
HOST_PREFIXES = ("www.", "m.", "amp.", "mobile.", "amp-")
INDEX_FILES = ("index.html", "index.htm", "index.php", "default.aspx")


def canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    host = (parts.hostname or "").lower()
    for prefix in HOST_PREFIXES:
        if host.startswith(prefix) and host.count(".") >= 2:
            host = host[len(prefix) :]
            break
    path = parts.path or "/"
    for index in INDEX_FILES:
        if path.endswith("/" + index):
            path = path[: -len(index)]
    path = path.removesuffix("/amp")
    if path.endswith("/amp/"):
        path = path[: -len("amp/")]
    path = path.rstrip("/") or "/"
    kept = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if key.lower() not in TRACKING_PARAMS
        and not key.lower().startswith(TRACKING_PREFIXES)
    )
    query = urlencode(kept)
    return urlunsplit((scheme, host, path, query, ""))


def url_key(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:32]
