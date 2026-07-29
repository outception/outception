"""Starter templates: curated source bundles by persona, resolved per IP
country the same way the default deck is (a Sports Fan in Dublin gets GAA and
the Premier League Table; in Dallas the NFL).

The registry stays server-side on purpose - editing a bundle is a backend
deploy, no client release. Clients own the display names/blurbs (i18n keyed by
template id); the API only ships ids.
"""

from dataclasses import dataclass
from typing import Any

from .cities_data import COUNTRY_TOP_CITY
from .endpoints import (
    COUNTRY_PODCAST,
    COUNTRY_SPORT_HEATMAPS,
    DEFAULT_PODCAST,
)
from .metadata import SOURCES
from .registry import DISABLED_SOURCES
from .shopping_data import (
    COUNTRY_BUSINESS,
    COUNTRY_DEALS,
    COUNTRY_EVENTS,
    COUNTRY_HEALTH,
    COUNTRY_PROPERTY,
    COUNTRY_TRAVEL,
)
from .teams_data import COUNTRY_SPORTS


@dataclass(frozen=True)
class Template:
    id: str
    # Static roster ids; country-resolved extras are appended by `resolve`.
    sources: tuple[str, ...]


_TEMPLATES: tuple[Template, ...] = (
    Template(
        "developer",
        (
            "github",
            "hackernews",
            "producthunt",
            "lobsters",
            "techcrunch",
            "theverge",
            "arstechnica",
            "youtube-theverge",
            "youtube-mkbhd",
            "openai",
            "tech-new",
            "heatmap-tech",
            "kickstarter",
            "sci-vibecoding",
            "sci-aicodingassistants",
        ),
    ),
    Template(
        "investor",
        (
            "heatmap-finance",
            "heatmap-tech",
            "marketwatch",
            "podcast-freakonomics",
            "podcast-planetmoney",
            "coindesk",
            "heatmap-crypto",
        ),
    ),
    Template(
        "news-junkie",
        (
            "bbc-world",
            "youtube-bbcnews",
            "cnn",
            "youtube-cnn",
            "guardian",
            "aljazeera",
            "dw",
            "france24",
            "time",
            "thehill",
            "podcast-thedailypodcast",
        ),
    ),
    Template(
        "sports-fan",
        (
            "bbcsport",
            "legalsportsreport",
            "podcast-newheightspodcast",
            "podcast-pardonmytake",
            "podcast-thebillsimmonspodcast",
        ),
    ),
    Template(
        "movie-buff",
        (
            "variety",
            "movie-new",
            "tv-new",
            "anime-new",
            "youtube-mrbeast",
            "podcast-smartless",
            "podcast-conanobrienneedsafriend",
        ),
    ),
    Template(
        "music-lover",
        (
            "music-new",
            "podcast-h3podcast",
        ),
    ),
    Template(
        "gamer",
        (
            "game-new",
            "heatmap-steam",
            "podcast-distractible",
        ),
    ),
    Template(
        "science-nerd",
        (
            "sciencedaily",
            "youtube-veritasium",
            "youtube-kurzgesagt",
            "youtube-vox",
            "podcast-radiolab",
            "podcast-hubermanlab",
            "podcast-lexfridmanpodcast",
        ),
    ),
    Template(
        "foodie-traveler",
        (
            "life-recipes",
            "youtube-markwiens",
            "life-budgettravel",
            "youtube-yestheory",
        ),
    ),
    Template(
        "comedy-fun",
        (
            "jokes",
            "quotes",
            "youtube-mrbeast",
            "podcast-2bears1cave",
            "podcast-badfriends",
            "podcast-flagrant",
        ),
    ),
    Template(
        "fitness-buff",
        (
            "gtopic-health",
            "life-fitness",
            "life-nutrition",
            "life-wellness",
            "life-mentalhealth",
            "life-sleepscience",
            "menshealth",
            "womenshealth",
            "podcast-hubermanlab",
            "youtube-athleanx",
            "youtube-chloeting",
            "heatmap-health-buzz",
        ),
    ),
    Template(
        "fashionista",
        (
            "life-fashion",
            "life-beauty",
            "life-skincare",
            "life-streetwear",
            "life-sneakers",
            "vogue",
            "wwd",
            "fashionista",
            "sneakernews",
            "whowhatwear",
            "youtube-hautelemode",
        ),
    ),
    Template(
        "petrolhead",
        (
            "car-new",
            "life-cars",
            "life-electriccars",
            "motor1",
            "caranddriver",
            "roadandtrack",
            "electrek",
            "insideevs",
            "youtube-carwow",
            "youtube-dougdemuro",
            "youtube-throttlehouse",
            "heatmap-f1",
            "sport-formula-1",
        ),
    ),
    Template(
        "crypto-trader",
        (
            "heatmap-crypto",
            "coindesk",
            "cointelegraph",
            "decrypt",
            "theblock",
            "bitcoinmagazine",
            "blockworks",
            "bankless",
            "gsearch-bitcoin",
            "gsearch-stablecoins",
        ),
    ),
    Template(
        "space-explorer",
        (
            "nasa",
            "space",
            "spacenews",
            "nasaspaceflight",
            "universetoday",
            "life-space",
            "gsearch-starship",
            "gsearch-jwst",
            "youtube-nasa",
            "youtube-spacex",
            "youtube-scottmanley",
            "youtube-pbsspacetime",
        ),
    ),
    Template(
        "ai-insider",
        (
            "openai",
            "deepmind",
            "googleai",
            "huggingface",
            "thedecoder",
            "gsearch-llm",
            "gsearch-agi",
            "tech-chatgpt",
            "tech-claudeai",
            "youtube-twominutepapers",
            "podcast-lexfridmanpodcast",
        ),
    ),
    Template(
        "true-crime",
        (
            "podcast-crimejunkie",
            "podcast-myfavoritemurder",
            "podcast-casefile",
            "podcast-morbid",
            "podcast-rottenmango",
            "podcast-serialpodcast",
            "podcast-datelinenbcpodcast",
            "youtube-mrballen",
            "themarshallproject",
            "courthousenews",
        ),
    ),
    Template(
        "history-buff",
        (
            "life-history",
            "life-ancienthistory",
            "life-archaeology",
            "historyextra",
            "smithsonianmag",
            "atlasobscura",
            "podcast-hardcorehistory",
            "podcast-therestishistory",
            "youtube-kingsandgenerals",
            "youtube-historymatters",
            "youtube-simplehistory",
        ),
    ),
    Template(
        "bookworm",
        (
            "book-new",
            "life-books",
            "life-bestsellers",
            "lithub",
            "kirkusreviews",
            "bookriot",
            "tordotcom",
            "theparisreview",
            "book-booktok",
            "gsearch-bestsellers",
        ),
    ),
    Template(
        "pop-culture",
        (
            "pagesix",
            "justjared",
            "vanityfair",
            "avclub",
            "life-celebritynews",
            "life-popculture",
            "royals",
            "horoscope-daily",
            "gsearch-celebrity",
            "gsearch-awardshows",
            "podcast-callherdaddy",
        ),
    ),
    Template(
        "esports-fan",
        (
            "sport-lol-esports",
            "sport-cs-esports",
            "esportsinsider",
            "dexerto",
            "heatmap-steam",
            "game-valorant",
            "game-leagueoflegends",
            "game-counterstrike2",
            "gsearch-esportstournament",
            "team-esports-t1esports",
            "team-esports-g2esports",
            "team-esports-fnatic",
        ),
    ),
    Template(
        "outdoors",
        (
            "life-hiking",
            "life-camping",
            "life-nationalparks",
            "life-nature",
            "life-wildlife",
            "gearjunkie",
            "outsideonline",
            "youtube-bbcearth",
            "gsearch-birdwatching",
            "gsearch-climbing",
        ),
    ),
    Template(
        "anime-manga",
        (
            "anime-new",
            "gsearch-anime",
            "life-anime",
            "life-manga",
            "life-comics",
            "life-cosplay",
            "life-fanculture",
        ),
    ),
    Template(
        "football-fan",
        (
            "bbcfootball",
            "sport-premier-league",
            "sport-champions-league",
            "sport-europa-league",
            "heatmap-premier-league",
            "heatmap-ucl",
            "youtube-brfootball",
            "youtube-daznfootball",
            "gsearch-fantasyfootball",
            "game-footballmanager",
        ),
    ),
    Template(
        "cricket-fan",
        (
            "heatmap-cricket",
            "sport-ipl",
            "sport-test-cricket",
            "sport-big-bash",
            "sport-the-hundred",
            "gsearch-cricket",
            "gsearch-cricketwc",
        ),
    ),
    Template(
        "fight-fan",
        (
            "heatmap-ufc",
            "sport-ufc",
            "sport-boxing",
            "youtube-ufc",
            "youtube-boxing",
            "youtube-daznboxing",
            "gsearch-ufc",
        ),
    ),
    Template(
        "deal-hunter",
        (
            "heatmap-deals-buzz",
            "dealcatcher",
            "branddeals-amazon",
            "branddeals-apple",
            "branddeals-nike",
            "branddeals-playstation",
            "branddeals-lego",
            "branddeals-ikea",
            "branddeals-costco",
            "life-frugalliving",
            "life-creditcards",
        ),
    ),
    Template(
        "personal-finance",
        (
            "life-personalfinance",
            "life-investing",
            "life-budgeting",
            "life-indexfunds",
            "life-retirement",
            "life-sidehustles",
            "life-passiveincome",
            "gsearch-personalfinance",
            "podcast-planetmoney",
            "youtube-whiteboardfinance",
            "youtube-theswedishinvestor",
            "book-thepsychologyofmoney",
        ),
    ),
    Template(
        "founder",
        (
            "producthunt",
            "kickstarter",
            "tcstartups",
            "eustartups",
            "gsearch-startups",
            "gsearch-startupfunding",
            "life-entrepreneurship",
            "life-smallbusiness",
            "podcast-howibuiltthis",
            "podcast-thediaryofaceo",
            "podcast-acquiredpodcast",
            "podcast-lennyspodcast",
        ),
    ),
    Template(
        "home-garden",
        (
            "life-interiordesign",
            "life-homedecor",
            "life-diyprojects",
            "life-gardening",
            "life-houseplants",
            "life-smarthome",
            "gsearch-homeimprovement",
            "gsearch-gardening",
            "branddeals-ikea",
        ),
    ),
    Template(
        "academia",
        (
            "insidehighered",
            "gsearch-universities",
            "gsearch-scholarships",
            "gsearch-studentloans",
            "gsearch-onlinecourses",
            "youtube-khanacademy",
            "youtube-crashcourse",
            "podcast-tedtalksdaily",
            "podcast-stuffyoushouldknow",
            "life-psychology",
            "life-philosophy",
            "life-productivity",
        ),
    ),
    Template(
        "researcher",
        (
            "nature",
            "newscientist",
            "physorg",
            "quanta",
            "scientificamerican",
            "technologyreview",
            "statnews",
            "sciencealert",
            "gsearch-brainresearch",
            "sci-nobelprize",
            "sci-clinicaltrials",
            "sci-peerreview",
        ),
    ),
    Template(
        "clean-energy",
        (
            "sci-fusionenergy",
            "sci-fusionprogress",
            "sci-greenhydrogen",
            "sci-hydrogenfuelcells",
            "sci-smallmodularreactors",
            "sci-solidstatebatteries",
            "sci-gridscalestorage",
            "sci-energytransition",
            "sci-enhancedgeothermal",
            "sci-airbornewindenergy",
            "sci-pylonwindturbines",
            "sci-plasticmagnets",
            "life-renewableenergy",
            "electrek",
            "heatmap-energy",
        ),
    ),
    Template(
        "photographer",
        (
            "petapixel",
            "life-photography",
            "life-photographygear",
            "life-travelphotography",
            "life-cameras",
            "gsearch-photoawards",
            "gsearch-filmphotography",
            "gsearch-photographytopic",
        ),
    ),
    Template("my-country", ()),
)


def _country_extras(template_id: str, cc: str | None) -> list[str]:
    """Country-resolved additions per template (empty when cc is unknown)."""
    if template_id == "sports-fan":
        extras = list(COUNTRY_SPORTS.get(cc or "") or ())
        extras += list(COUNTRY_SPORT_HEATMAPS.get(cc or "") or ("heatmap-ucl",))
        return extras
    if template_id == "investor" and cc:
        return [
            sid for sid in (COUNTRY_BUSINESS.get(cc), COUNTRY_PROPERTY.get(cc)) if sid
        ]
    if template_id == "foodie-traveler" and cc:
        return [sid for sid in (COUNTRY_TRAVEL.get(cc), COUNTRY_DEALS.get(cc)) if sid]
    if template_id == "fitness-buff" and cc:
        return [sid for sid in (COUNTRY_HEALTH.get(cc),) if sid]
    if template_id == "deal-hunter" and cc:
        return [sid for sid in (COUNTRY_DEALS.get(cc),) if sid]
    if template_id == "founder" and cc:
        return [sid for sid in (COUNTRY_BUSINESS.get(cc),) if sid]
    if template_id == "home-garden" and cc:
        return [sid for sid in (COUNTRY_PROPERTY.get(cc),) if sid]
    if template_id == "academia" and cc:
        return [f"education-{cc.lower()}"]
    if template_id == "movie-buff":
        return [COUNTRY_PODCAST.get(cc or "", DEFAULT_PODCAST)]
    if template_id == "my-country" and cc:
        return [
            sid
            for sid in (
                f"gnews-{cc.lower()}",
                COUNTRY_TOP_CITY.get(cc),
                COUNTRY_PROPERTY.get(cc),
                COUNTRY_BUSINESS.get(cc),
                COUNTRY_EVENTS.get(cc),
                COUNTRY_HEALTH.get(cc),
                COUNTRY_DEALS.get(cc),
            )
            if sid
        ]
    return []


def resolve_templates(cc: str | None) -> list[dict[str, Any]]:
    """Every template with its final, validated source list for this country.
    Unknown/disabled/key-gated ids drop out (mirrors the default deck), and a
    template that resolves empty is omitted entirely (e.g. "my-country" for an
    unknown visitor)."""
    out: list[dict[str, Any]] = []
    for template in _TEMPLATES:
        ids = list(template.sources) + _country_extras(template.id, cc)
        seen: set[str] = set()
        sources: list[str] = []
        for sid in ids:
            if sid in seen or sid not in SOURCES or sid in DISABLED_SOURCES:
                continue
            seen.add(sid)
            sources.append(sid)
        if sources:
            out.append({"id": template.id, "sources": sources})
    return out
