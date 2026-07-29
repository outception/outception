"""Additional YouTube channels — the biggest creators per category.

Every channel id here was resolved and verified against its live Atom feed
(title match) so there are no dead cards. Data only; ``sources/youtube.py``
registers the getters and ``metadata.py`` builds the ``SOURCES`` rows. Ids that
already exist in the base channel list are skipped at wiring time.
"""

from __future__ import annotations

# (channel_id, source_id, display_name, column)
YOUTUBE_EXTRA: list[tuple[str, str, str, str]] = [
    ("UCyEd6QBSgat5kkC6svyjudA", "youtube-markwiens", "Mark Wiens", "food"),
    ("UCsqjHFMB_JYTaEnf_vmTNqg", "youtube-dougdemuro", "Doug DeMuro", "tech"),
    (
        "UCHkj014U2CQ2Nv0UZeYpE_A",
        "youtube-justinbieber",
        "Justin Bieber",
        "entertainment",
    ),
    (
        "UCiGm_E4ZwYSHV3bcW1pnSeQ",
        "youtube-billieeilish",
        "Billie Eilish",
        "entertainment",
    ),
    ("UCJplp5SjeGSdVdwsfb9Q7lQ", "youtube-likenastya", "Like Nastya", "entertainment"),
    ("UCvlE5gTbOvjiolFlEm-c_Ow", "youtube-vladniki", "Vlad and Niki", "entertainment"),
    (
        "UCIPPMRA040LQr5QPyJEbmXA",
        "youtube-mrbeastgaming",
        "MrBeast Gaming",
        "entertainment",
    ),
    ("UCJHA_jMfCvEnv-3kRjTCQXw", "youtube-babish", "Binging with Babish", "food"),
    # Batch 2 — more verified channels per category
    ("UC_hK9fOxyy_TM8FJGXIyG8Q", "youtube-dharmann", "Dhar Mann", "entertainment"),
    ("UCnmGIkw-KdI0W5siakKPKog", "youtube-ryantrahan", "Ryan Trahan", "entertainment"),
    (
        "UC6107grRI4m0o2-emgoDnAA",
        "youtube-smartereveryday",
        "SmarterEveryDay",
        "science",
    ),
    ("UCfM3zsQsOnfWNUppiycmBuw", "youtube-eminem", "Eminem", "entertainment"),
    ("UCCgLoMYIyP0U56dEhEL1wXQ", "youtube-chloeting", "Chloe Ting", "lifestyle"),
    (
        "UC78cxCAcp7JfQPgKxYdyGrg",
        "youtube-emmachamberlain",
        "Emma Chamberlain",
        "lifestyle",
    ),
    # Shopping verticals — cars / property / travel / fashion
    ("UCUhFaUpnq31m6TNX2VKVSVA", "youtube-carwow", "carwow", "cars"),
    ("UCKSVUHI9rbbkXhvAXK-2uxA", "youtube-supercarblondie", "Supercar Blondie", "cars"),
    ("UCyXiDU5qjfOPxgOPeFWGwKw", "youtube-throttlehouse", "Throttle House", "cars"),
    ("UCHWbZM3BIGgZksvXegx_h3w", "youtube-enesyilmazer", "Enes Yilmazer", "property"),
    ("UC4ijq8Cg-8zQKx8OH12dUSw", "youtube-karaandnate", "Kara and Nate", "travel"),
    ("UC0Ize0RLIbGdH5x4wI45G-A", "youtube-drewbinsky", "Drew Binsky", "travel"),
    ("UCvK4bOhULCpmLabd2pDMtnA", "youtube-yestheory", "Yes Theory", "travel"),
    ("UCoEj4uRzynPXEEegNqMnJVw", "youtube-hautelemode", "HauteLeMode", "entertainment"),
]
