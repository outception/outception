"""Shopping-vertical feeds — deals, property, cars and travel-deal sources.

Two families, both plain data (no imports from metadata/sources to avoid
circular dependencies, mirroring ``life_data``):

* ``SHOPPING_FEEDS`` — direct RSS/Atom feeds of real deal communities and
  buying-editorial sites. Every URL here was fetched and returned a valid
  feed before being added; listing portals (Daft, Zillow, Rightmove, …)
  publish no feeds and are deliberately absent.
* ``SHOPPING_SEARCHES`` — per-country Google News searches, query localised
  to the country's language, so every market gets a Deals and a Property
  card even where no community feed exists. Same machinery as the country
  news editions.

``COUNTRY_DEALS`` / ``COUNTRY_PROPERTY`` name the best source per country so
the default deck can lead with the visitor's own market (CF-IPCountry),
exactly like national news and city cards do.
"""

from __future__ import annotations

# (source_id, feed_url, display_name, column, homepage)
ShoppingFeed = tuple[str, str, str, str, str]

SHOPPING_FEEDS: list[ShoppingFeed] = [
    # ---- Deals: community-curated bargain sites (the Pepper network + kin) --
    (
        "hotukdeals",
        "https://www.hotukdeals.com/rss/hot",
        "hotukdeals",
        "deals",
        "https://www.hotukdeals.com",
    ),
    (
        "mydealz",
        "https://www.mydealz.de/rss/hot",
        "mydealz",
        "deals",
        "https://www.mydealz.de",
    ),
    (
        "dealabs",
        "https://www.dealabs.com/rss/hot",
        "Dealabs",
        "deals",
        "https://www.dealabs.com",
    ),
    (
        "chollometro",
        "https://www.chollometro.com/rss/hot",
        "Chollometro",
        "deals",
        "https://www.chollometro.com",
    ),
    (
        "peppernl",
        "https://nl.pepper.com/rss/hot",
        "Pepper NL",
        "deals",
        "https://nl.pepper.com",
    ),
    (
        "pepperpl",
        "https://www.pepper.pl/rss/hot",
        "Pepper PL",
        "deals",
        "https://www.pepper.pl",
    ),
    (
        "promodescuentos",
        "https://www.promodescuentos.com/rss/hot",
        "PromoDescuentos",
        "deals",
        "https://www.promodescuentos.com",
    ),
    (
        "preisjaeger",
        "https://www.preisjaeger.at/rss/hot",
        "Preisjäger",
        "deals",
        "https://www.preisjaeger.at",
    ),
    (
        "preispirat",
        "https://www.preispirat.ch/feed",
        "Preispirat",
        "deals",
        "https://www.preispirat.ch",
    ),
    (
        "slickdeals",
        "https://feeds.feedburner.com/SlickdealsnetFP",
        "Slickdeals",
        "deals",
        "https://slickdeals.net",
    ),
    (
        "dealcatcher",
        "https://www.dealcatcher.com/rss",
        "DealCatcher",
        "deals",
        "https://www.dealcatcher.com",
    ),
    (
        "ozbargain",
        "https://www.ozbargain.com.au/deals/feed",
        "OzBargain",
        "deals",
        "https://www.ozbargain.com.au",
    ),
    (
        "cheapies",
        "https://www.cheapies.nz/deals/feed",
        "Cheapies",
        "deals",
        "https://www.cheapies.nz",
    ),
    (
        "singpromos",
        "https://singpromos.com/feed/",
        "SingPromos",
        "deals",
        "https://singpromos.com",
    ),
    # ---- Ideas & fundraising: crowdfunding launches + startup press (tech) --
    (
        "kickstarter",
        "https://www.kickstarter.com/projects/feed.atom",
        "Kickstarter",
        "tech",
        "https://www.kickstarter.com/discover",
    ),
    (
        "crowdfundinsider",
        "https://www.crowdfundinsider.com/feed/",
        "Crowdfund Insider",
        "tech",
        "https://www.crowdfundinsider.com",
    ),
    (
        "tcstartups",
        "https://techcrunch.com/category/startups/feed/",
        "TC Startups",
        "tech",
        "https://techcrunch.com/category/startups/",
    ),
    (
        "eustartups",
        "https://www.eu-startups.com/feed/",
        "EU-Startups",
        "tech",
        "https://www.eu-startups.com",
    ),
    (
        "ycblog",
        "https://www.ycombinator.com/blog/rss",
        "Y Combinator",
        "tech",
        "https://www.ycombinator.com/blog",
    ),
    # ---- Travel deals & destinations (existing travel column) ---------------
    (
        "fly4free",
        "https://www.fly4free.com/feed/",
        "Fly4free",
        "travel",
        "https://www.fly4free.com",
    ),
    (
        "travelfree",
        "https://travelfree.info/feed/",
        "TravelFree",
        "travel",
        "https://travelfree.info",
    ),
    (
        "theflightdeal",
        "https://www.theflightdeal.com/feed/",
        "The Flight Deal",
        "travel",
        "https://www.theflightdeal.com",
    ),
    (
        "headforpoints",
        "https://www.headforpoints.com/feed/",
        "Head for Points",
        "travel",
        "https://www.headforpoints.com",
    ),
    (
        "onemileatatime",
        "https://onemileatatime.com/feed/",
        "One Mile at a Time",
        "travel",
        "https://onemileatatime.com",
    ),
    (
        "cntraveler",
        "https://news.google.com/rss/search?q=site:cntraveler.com&hl=en-US&gl=US&ceid=US:en",
        "Condé Nast Traveler",
        "travel",
        "https://www.cntraveler.com",
    ),
    # ---- Travel Pirates network — holiday-deal editors per market ----------
    (
        "holidaypirates",
        "https://www.holidaypirates.com/feed",
        "HolidayPirates",
        "travel",
        "https://www.holidaypirates.com",
    ),
    (
        "travelpirates",
        "https://www.travelpirates.com/feed",
        "TravelPirates",
        "travel",
        "https://www.travelpirates.com",
    ),
    (
        "urlaubspiraten",
        "https://www.urlaubspiraten.de/feed",
        "Urlaubspiraten",
        "travel",
        "https://www.urlaubspiraten.de",
    ),
    (
        "voyagespirates",
        "https://www.voyagespirates.fr/feed",
        "VoyagesPirates",
        "travel",
        "https://www.voyagespirates.fr",
    ),
    (
        "piratinviaggio",
        "https://www.piratinviaggio.it/feed",
        "PiratinViaggio",
        "travel",
        "https://www.piratinviaggio.it",
    ),
    (
        "viajerospiratas",
        "https://www.viajerospiratas.es/feed",
        "ViajerosPiratas",
        "travel",
        "https://www.viajerospiratas.es",
    ),
    (
        "wakacyjnipiraci",
        "https://www.wakacyjnipiraci.pl/feed",
        "WakacyjniPiraci",
        "travel",
        "https://www.wakacyjnipiraci.pl",
    ),
    # ---- Gaming deals (deals column — it's shopping, not games press) -------
    (
        "indiegamebundles",
        "https://www.indiegamebundles.com/feed/",
        "IndieGameBundles",
        "deals",
        "https://www.indiegamebundles.com",
    ),
    (
        "ggdeals",
        "https://gg.deals/news/feed/",
        "GG.deals",
        "deals",
        "https://gg.deals",
    ),
    # ---- Niche buying editorial: sneakers, beauty (entertainment column,
    # with the fashion sources) -------------------------------------------
    (
        "sneakernews",
        "https://sneakernews.com/feed/",
        "Sneaker News",
        "entertainment",
        "https://sneakernews.com",
    ),
    (
        "nicekicks",
        "https://www.nicekicks.com/feed/",
        "Nice Kicks",
        "entertainment",
        "https://www.nicekicks.com",
    ),
    # ---- Architecture & interiors (property column) -------------------------
    (
        "wallpaperdesign",
        "https://www.wallpaper.com/feeds/all",
        "Wallpaper*",
        "property",
        "https://www.wallpaper.com",
    ),
    # ---- Property: market news & buying editorial ---------------------------
    (
        "propertyindustryeye",
        "https://propertyindustryeye.com/feed/",
        "Property Industry Eye",
        "property",
        "https://propertyindustryeye.com",
    ),
    (
        "realtornews",
        "https://www.realtor.com/news/feed/",
        "Realtor.com News",
        "property",
        "https://www.realtor.com/news/",
    ),
    (
        "housebeautiful",
        "https://www.housebeautiful.com/rss/all.xml/",
        "House Beautiful",
        "property",
        "https://www.housebeautiful.com",
    ),
    (
        "biggerpockets",
        "https://www.biggerpockets.com/blog/feed",
        "BiggerPockets",
        "property",
        "https://www.biggerpockets.com/blog",
    ),
    (
        "realestateau",
        "https://www.realestate.com.au/news/feed/",
        "realestate.com.au",
        "property",
        "https://www.realestate.com.au/news/",
    ),
    (
        "storeys",
        "https://storeys.com/feed/",
        "Storeys",
        "property",
        "https://storeys.com",
    ),
    (
        "stackedhomes",
        "https://stackedhomes.com/editorial/feed/",
        "Stacked Homes",
        "property",
        "https://stackedhomes.com",
    ),
    (
        "spanishpropertyinsight",
        "https://www.spanishpropertyinsight.com/feed/",
        "Spanish Property Insight",
        "property",
        "https://www.spanishpropertyinsight.com",
    ),
    (
        "frenchentree",
        "https://www.frenchentree.com/feed/",
        "FrenchEntrée",
        "property",
        "https://www.frenchentree.com",
    ),
    (
        "propertywire",
        "https://www.propertywire.com/feed/",
        "Property Wire",
        "property",
        "https://www.propertywire.com",
    ),
    # ---- Cars: buying advice, reviews, market news (existing cars column) ---
    (
        "autocaruk",
        "https://www.autocar.co.uk/rss",
        "Autocar",
        "cars",
        "https://www.autocar.co.uk",
    ),
    (
        "autoexpress",
        "https://www.autoexpress.co.uk/feed/all",
        "Auto Express",
        "cars",
        "https://www.autoexpress.co.uk",
    ),
    (
        "cardealermag",
        "https://cardealermagazine.co.uk/feed",
        "Car Dealer",
        "cars",
        "https://cardealermagazine.co.uk",
    ),
    (
        "gaadiwaadi",
        "https://gaadiwaadi.com/feed/",
        "GaadiWaadi",
        "cars",
        "https://gaadiwaadi.com",
    ),
    # ---- Fashion / style shopping editorial (entertainment column, with
    # vogue/hypebeast/fashionista/gq) --------------------------------------
    (
        "whowhatwear",
        "https://www.whowhatwear.com/rss",
        "Who What Wear",
        "entertainment",
        "https://www.whowhatwear.com",
    ),
    (
        "esquirestyle",
        "https://www.esquire.com/rss/all.xml/",
        "Esquire",
        "entertainment",
        "https://www.esquire.com",
    ),
    # ---- Batch 3: worldwide verticals (agent-verified feeds, 2026-08-07) ---
    (
        "ppomppu",
        "https://www.ppomppu.co.kr/rss.php?id=ppomppu",
        "Ppomppu",
        "deals",
        "https://www.ppomppu.co.kr",
    ),
    (
        "scontomaggio",
        "https://www.scontomaggio.com/feed",
        "scontOmaggio",
        "deals",
        "https://www.scontomaggio.com",
    ),
    (
        "dimmicosacerchi",
        "https://www.dimmicosacerchi.it/feed",
        "DimmiCosaCerchi",
        "deals",
        "https://www.dimmicosacerchi.it",
    ),
    (
        "everydayonsales",
        "https://news.google.com/rss/search?q=site:everydayonsales.com&hl=en-MY&gl=MY&ceid=MY:en",
        "EverydayOnSales",
        "deals",
        "https://www.everydayonsales.com",
    ),
    (
        "idealistait",
        "https://www.idealista.it/news/rss/v2/latest-news.xml",
        "Idealista IT",
        "property",
        "https://www.idealista.it/news/",
    ),
    (
        "idealistapt",
        "https://www.idealista.pt/news/rss/v2/latest-news.xml",
        "Idealista PT",
        "property",
        "https://www.idealista.pt/news/",
    ),
    (
        "idealistaes",
        "https://www.idealista.com/news/rss/v2/latest-news.xml",
        "Idealista",
        "property",
        "https://www.idealista.com/news/",
    ),
    (
        "loftblog",
        "https://blog.loft.com.br/feed",
        "Loft",
        "property",
        "https://blog.loft.com.br",
    ),
    (
        "realestatejapan",
        "https://resources.realestate.co.jp/feed/",
        "Real Estate Japan",
        "property",
        "https://resources.realestate.co.jp",
    ),
    (
        "globesnadlan",
        "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=607",
        "Globes Nadlan",
        "property",
        "https://www.globes.co.il",
    ),
    (
        "emlaknews",
        "https://www.emlaknews.com.tr/rss",
        "EmlakNews",
        "property",
        "https://www.emlaknews.com.tr",
    ),
    (
        "portfolioingatlan",
        "https://www.portfolio.hu/rss/ingatlan.xml",
        "Portfolio Ingatlan",
        "property",
        "https://www.portfolio.hu/ingatlan",
    ),
    (
        "hypoindex",
        "https://www.hypoindex.cz/feed/",
        "Hypoindex",
        "property",
        "https://www.hypoindex.cz",
    ),
    (
        "kiinteistolehti",
        "https://www.kiinteistolehti.fi/feed/",
        "Kiinteistölehti",
        "property",
        "https://www.kiinteistolehti.fi",
    ),
    (
        "edgeprop",
        "https://www.edgeprop.my/rss.xml",
        "EdgeProp",
        "property",
        "https://www.edgeprop.my",
    ),
    (
        "vnexpressbds",
        "https://vnexpress.net/rss/bat-dong-san.rss",
        "VnExpress BĐS",
        "property",
        "https://vnexpress.net/bat-dong-san",
    ),
    (
        "lamudiph",
        "https://www.lamudi.com.ph/journal/feed/",
        "Lamudi PH",
        "property",
        "https://www.lamudi.com.ph/journal/",
    ),
    (
        "squareyards",
        "https://www.squareyards.com/blog/feed",
        "Square Yards",
        "property",
        "https://www.squareyards.com/blog",
    ),
    (
        "buyrentkenya",
        "https://www.buyrentkenya.com/discover/feed",
        "BuyRentKenya",
        "property",
        "https://www.buyrentkenya.com/discover",
    ),
    (
        "interestnz",
        "https://www.interest.co.nz/rss",
        "interest.co.nz",
        "property",
        "https://www.interest.co.nz",
    ),
    (
        "motoriit",
        "https://www.motori.it/feed",
        "Motori.it",
        "cars",
        "https://www.motori.it",
    ),
    (
        "quatrorodas",
        "https://quatrorodas.abril.com.br/feed/",
        "Quatro Rodas",
        "cars",
        "https://quatrorodas.abril.com.br",
    ),
    (
        "responsejp",
        "https://response.jp/rss/index.rdf",
        "Response",
        "cars",
        "https://response.jp",
    ),
    (
        "motorgraph",
        "https://www.motorgraph.com/rss/allArticle.xml",
        "Motorgraph",
        "cars",
        "https://www.motorgraph.com",
    ),
    (
        "automotorsportse",
        "https://www.automotorsport.se/feed",
        "Auto Motor & Sport",
        "cars",
        "https://www.automotorsport.se",
    ),
    (
        "bilmagasinet",
        "https://bilmagasinet.dk/feed/rss",
        "Bilmagasinet",
        "cars",
        "https://bilmagasinet.dk",
    ),
    (
        "moottori",
        "https://www.moottori.fi/feed/",
        "Moottori",
        "cars",
        "https://www.moottori.fi",
    ),
    (
        "razaoautomovel",
        "https://razaoautomovel.com/feed",
        "Razão Automóvel",
        "cars",
        "https://razaoautomovel.com",
    ),
    (
        "caroto",
        "https://www.caroto.gr/feed/",
        "Caroto",
        "cars",
        "https://www.caroto.gr",
    ),
    (
        "autocz",
        "https://www.auto.cz/rss",
        "Auto.cz",
        "cars",
        "https://www.auto.cz",
    ),
    (
        "vezess",
        "https://www.vezess.hu/feed/",
        "Vezess",
        "cars",
        "https://www.vezess.hu",
    ),
    (
        "automarketro",
        "https://www.automarket.ro/rss/",
        "Automarket",
        "cars",
        "https://www.automarket.ro",
    ),
    (
        "otoaktuel",
        "https://www.otoaktuel.com.tr/rss",
        "OtoAktuel",
        "cars",
        "https://www.otoaktuel.com.tr",
    ),
    (
        "parabrisas",
        "https://parabrisas.perfil.com/feed",
        "Parabrisas",
        "cars",
        "https://parabrisas.perfil.com",
    ),
    (
        "rutamotor",
        "https://www.rutamotor.com/feed/",
        "Rutamotor",
        "cars",
        "https://www.rutamotor.com",
    ),
    (
        "paultan",
        "https://paultan.org/feed/",
        "Paul Tan",
        "cars",
        "https://paultan.org",
    ),
    (
        "headlightmag",
        "https://news.google.com/rss/search?q=site:headlightmag.com&hl=th&gl=TH&ceid=TH:th",
        "HeadLight Mag",
        "cars",
        "https://www.headlightmag.com",
    ),
    (
        "vnexpressoto",
        "https://vnexpress.net/rss/oto-xe-may.rss",
        "VnExpress Ô tô",
        "cars",
        "https://vnexpress.net/oto-xe-may",
    ),
    (
        "autonetmagz",
        "https://www.autonetmagz.com/feed/",
        "AutonetMagz",
        "cars",
        "https://www.autonetmagz.com",
    ),
    (
        "visorph",
        "https://visor.ph/feed/",
        "Visor",
        "cars",
        "https://visor.ph",
    ),
    (
        "tsamotoring",
        "https://www.thesouthafrican.com/motoring/feed/",
        "TSA Motoring",
        "cars",
        "https://www.thesouthafrican.com/motoring/",
    ),
    (
        "autojosh",
        "https://autojosh.com/feed/",
        "AutoJosh",
        "cars",
        "https://autojosh.com",
    ),
    (
        "arabgt",
        "https://www.arabgt.com/feed",
        "ArabGT",
        "cars",
        "https://www.arabgt.com",
    ),
    (
        "ferienpiraten",
        "https://www.ferienpiraten.ch/feed",
        "Ferienpiraten",
        "travel",
        "https://www.ferienpiraten.ch",
    ),
    (
        "vakantiepiraten",
        "https://www.vakantiepiraten.nl/feed",
        "VakantiePiraten",
        "travel",
        "https://www.vakantiepiraten.nl",
    ),
    (
        "melhoresdestinos",
        "https://feeds.feedburner.com/melhoresdestinos",
        "Melhores Destinos",
        "travel",
        "https://www.melhoresdestinos.com.br",
    ),
    (
        "traicy",
        "https://www.traicy.com/feed",
        "Traicy",
        "travel",
        "https://www.traicy.com",
    ),
    (
        "milemoa",
        "https://www.milemoa.com/bbs/rss",
        "Milemoa",
        "travel",
        "https://www.milemoa.com",
    ),
    (
        "insideflyerdk",
        "https://insideflyer.dk/feed/",
        "InsideFlyer DK",
        "travel",
        "https://insideflyer.dk",
    ),
    (
        "insideflyerno",
        "https://insideflyer.no/feed/",
        "InsideFlyer NO",
        "travel",
        "https://insideflyer.no",
    ),
    (
        "insideflyerse",
        "https://insideflyer.se/feed/",
        "InsideFlyer SE",
        "travel",
        "https://insideflyer.se",
    ),
    (
        "zaletsi",
        "https://news.google.com/rss/search?q=site:zaletsi.cz&hl=cs&gl=CZ&ceid=CZ:cs",
        "Zaletsi",
        "travel",
        "https://www.zaletsi.cz",
    ),
    (
        "travelgr",
        "https://www.travel.gr/feed/",
        "Travel.gr",
        "travel",
        "https://www.travel.gr",
    ),
    (
        "promocionesaereas",
        "https://www.promociones-aereas.com.ar/feed",
        "Promociones Aéreas",
        "travel",
        "https://www.promociones-aereas.com.ar",
    ),
    (
        "vnexpressdulich",
        "https://vnexpress.net/rss/du-lich.rss",
        "VnExpress Du lịch",
        "travel",
        "https://vnexpress.net/du-lich",
    ),
    (
        "milelion",
        "https://milelion.com/feed/",
        "The MileLion",
        "travel",
        "https://milelion.com",
    ),
    (
        "livefromalounge",
        "https://livefromalounge.com/feed/",
        "Live From A Lounge",
        "travel",
        "https://livefromalounge.com",
    ),
    (
        "travelstart",
        "https://www.travelstart.co.za/blog/feed",
        "Travelstart",
        "travel",
        "https://www.travelstart.co.za/blog",
    ),
    (
        "iknowthepilot",
        "https://iknowthepilot.com.au/feed",
        "I Know The Pilot",
        "travel",
        "https://iknowthepilot.com.au",
    ),
    (
        "samchui",
        "https://samchui.com/feed/",
        "Sam Chui",
        "travel",
        "https://samchui.com",
    ),
    (
        "loyaltylobby",
        "https://www.loyaltylobby.com/feed/",
        "LoyaltyLobby",
        "travel",
        "https://www.loyaltylobby.com",
    ),
]

# Per-country Google News searches for markets without (or beyond) a direct
# community feed: (cc, hl, country_name, property_query, deals_query).
# Queries are in the market's dominant language so the feed surfaces local
# outlets, mirroring how the country news editions localise.
_COUNTRY_SEARCHES: list[tuple[str, str, str, str, str]] = [
    ("IE", "en-IE", "Ireland", "property market Ireland", "deals discounts Ireland"),
    ("GB", "en-GB", "UK", "UK housing market", ""),
    ("US", "en-US", "US", "US housing market", ""),
    ("DE", "de", "Germany", "Immobilienmarkt", ""),
    ("FR", "fr", "France", "marché immobilier", ""),
    ("ES", "es", "Spain", "mercado inmobiliario", ""),
    ("IT", "it", "Italy", "mercato immobiliare", "offerte sconti"),
    ("PT", "pt-PT", "Portugal", "mercado imobiliário", "promoções descontos"),
    ("NL", "nl", "Netherlands", "woningmarkt", ""),
    ("BE", "nl", "Belgium", "vastgoedmarkt België", "aanbiedingen kortingen België"),
    ("PL", "pl", "Poland", "rynek nieruchomości", ""),
    ("SE", "sv", "Sweden", "bostadsmarknaden", "erbjudanden rea"),
    ("NO", "no", "Norway", "boligmarkedet", "tilbud salg"),
    ("DK", "da", "Denmark", "boligmarked", "tilbud udsalg"),
    ("FI", "fi", "Finland", "asuntomarkkinat", "tarjoukset alennukset"),
    ("AT", "de", "Austria", "Immobilienmarkt Österreich", ""),
    ("CH", "de", "Switzerland", "Immobilienmarkt Schweiz", ""),
    ("CZ", "cs", "Czechia", "trh nemovitostí", "slevy akce"),
    ("HU", "hu", "Hungary", "ingatlanpiac", "akciók kedvezmények"),
    ("RO", "ro", "Romania", "piața imobiliară", "oferte reduceri"),
    ("GR", "el", "Greece", "αγορά ακινήτων", "προσφορές εκπτώσεις"),
    ("TR", "tr", "Turkey", "konut piyasası", "indirim kampanya"),
    ("CA", "en-CA", "Canada", "Canada housing market", "Canada deals sales"),
    ("MX", "es-419", "Mexico", "mercado inmobiliario México", ""),
    (
        "BR",
        "pt-BR",
        "Brazil",
        "mercado imobiliário Brasil",
        "promoções descontos Brasil",
    ),
    (
        "AR",
        "es-419",
        "Argentina",
        "mercado inmobiliario Argentina",
        "ofertas descuentos Argentina",
    ),
    ("CL", "es-419", "Chile", "mercado inmobiliario Chile", "ofertas descuentos Chile"),
    (
        "CO",
        "es-419",
        "Colombia",
        "mercado inmobiliario Colombia",
        "ofertas descuentos Colombia",
    ),
    ("AU", "en-AU", "Australia", "Australia housing market", ""),
    ("NZ", "en-NZ", "New Zealand", "New Zealand housing market", ""),
    ("JP", "ja", "Japan", "不動産市場", "セール 割引"),
    ("KR", "ko", "South Korea", "부동산 시장", "할인 특가"),
    ("IN", "en-IN", "India", "India property market", "India deals offers"),
    ("SG", "en-SG", "Singapore", "Singapore property market", ""),
    (
        "MY",
        "en-MY",
        "Malaysia",
        "Malaysia property market",
        "Malaysia deals promotions",
    ),
    (
        "PH",
        "en-PH",
        "Philippines",
        "Philippines real estate",
        "Philippines deals promos",
    ),
    ("ID", "id", "Indonesia", "pasar properti", "promo diskon"),
    ("TH", "th", "Thailand", "ตลาดอสังหาริมทรัพย์", "โปรโมชั่น ส่วนลด"),
    ("VN", "vi", "Vietnam", "thị trường bất động sản", "khuyến mãi giảm giá"),
    ("AE", "en", "UAE", "Dubai property market", "UAE deals offers"),
    ("IL", "iw", "Israel", "שוק הנדלן", "מבצעים הנחות"),
    (
        "ZA",
        "en-ZA",
        "South Africa",
        "South Africa property market",
        "South Africa deals specials",
    ),
    ("NG", "en-NG", "Nigeria", "Nigeria real estate", "Nigeria deals discounts"),
    ("KE", "en-KE", "Kenya", "Kenya real estate", "Kenya deals offers"),
    ("EG", "ar", "Egypt", "سوق العقارات مصر", "عروض وخصومات مصر"),
    ("SA", "ar", "Saudi Arabia", "سوق العقارات السعودية", "عروض وخصومات السعودية"),
]


def _search_url(query: str, hl: str, cc: str, recency: str = "") -> str:
    q = query.replace(" ", "+")
    if recency:
        q += f"+when:{recency}"
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={cc}&ceid={cc}:{hl}"


# (source_id, feed_url, display_name, kicker, column)
ShoppingSearch = tuple[str, str, str, str, str]

# Big-store sale cards: one entity feed per major retailer/brand, via the
# same Google News search machinery as team/brand feeds — stores publish
# no sale RSS themselves, but sale coverage is news within minutes.
BRAND_DEAL_SEARCHES: list[ShoppingSearch] = [
    (
        "branddeals-apple",
        "https://news.google.com/rss/search?q=Apple+deals+discount&hl=en-US&gl=US&ceid=US:en",
        "Apple Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-nike",
        "https://news.google.com/rss/search?q=Nike+sale+discount&hl=en-US&gl=US&ceid=US:en",
        "Nike Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-adidas",
        "https://news.google.com/rss/search?q=Adidas+sale+discount&hl=en-US&gl=US&ceid=US:en",
        "Adidas Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-amazon",
        "https://news.google.com/rss/search?q=Amazon+deals+today&hl=en-US&gl=US&ceid=US:en",
        "Amazon Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-samsung",
        "https://news.google.com/rss/search?q=Samsung+deals+discount&hl=en-US&gl=US&ceid=US:en",
        "Samsung Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-playstation",
        "https://news.google.com/rss/search?q=PlayStation+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "PlayStation Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-xbox",
        "https://news.google.com/rss/search?q=Xbox+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Xbox Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-nintendo",
        "https://news.google.com/rss/search?q=Nintendo+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Nintendo Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-lego",
        "https://news.google.com/rss/search?q=Lego+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Lego Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-ikea",
        "https://news.google.com/rss/search?q=IKEA+sale+offers&hl=en-US&gl=US&ceid=US:en",
        "IKEA Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-zara",
        "https://news.google.com/rss/search?q=Zara+sale+collection&hl=en-US&gl=US&ceid=US:en",
        "Zara Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-hm",
        "https://news.google.com/rss/search?q=H%26M+sale+collection&hl=en-US&gl=US&ceid=US:en",
        "H&M Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-uniqlo",
        "https://news.google.com/rss/search?q=Uniqlo+sale+collection&hl=en-US&gl=US&ceid=US:en",
        "Uniqlo Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-primark",
        "https://news.google.com/rss/search?q=Primark+new+in+prices&hl=en-US&gl=US&ceid=US:en",
        "Primark Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-sephora",
        "https://news.google.com/rss/search?q=Sephora+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Sephora Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-costco",
        "https://news.google.com/rss/search?q=Costco+deals&hl=en-US&gl=US&ceid=US:en",
        "Costco Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-walmart",
        "https://news.google.com/rss/search?q=Walmart+deals&hl=en-US&gl=US&ceid=US:en",
        "Walmart Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-target",
        "https://news.google.com/rss/search?q=Target+deals+sale&hl=en-US&gl=US&ceid=US:en",
        "Target Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-bestbuy",
        "https://news.google.com/rss/search?q=Best+Buy+deals&hl=en-US&gl=US&ceid=US:en",
        "Best Buy Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-aldi",
        "https://news.google.com/rss/search?q=Aldi+offers+specialbuys&hl=en-US&gl=US&ceid=US:en",
        "Aldi Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-lidl",
        "https://news.google.com/rss/search?q=Lidl+offers+middle+aisle&hl=en-US&gl=US&ceid=US:en",
        "Lidl Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-tesco",
        "https://news.google.com/rss/search?q=Tesco+clubcard+offers&hl=en-US&gl=US&ceid=US:en",
        "Tesco Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-currys",
        "https://news.google.com/rss/search?q=Currys+deals&hl=en-US&gl=US&ceid=US:en",
        "Currys Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-argos",
        "https://news.google.com/rss/search?q=Argos+deals&hl=en-US&gl=US&ceid=US:en",
        "Argos Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-jdsports",
        "https://news.google.com/rss/search?q=JD+Sports+sale&hl=en-US&gl=US&ceid=US:en",
        "JD Sports Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-decathlon",
        "https://news.google.com/rss/search?q=Decathlon+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Decathlon Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-dyson",
        "https://news.google.com/rss/search?q=Dyson+sale+deal&hl=en-US&gl=US&ceid=US:en",
        "Dyson Deals",
        "Deals",
        "deals",
    ),
    (
        "branddeals-shein",
        "https://news.google.com/rss/search?q=Shein+sale+haul&hl=en-US&gl=US&ceid=US:en",
        "Shein Deals",
        "Deals",
        "deals",
    ),
]

SHOPPING_SEARCHES: list[ShoppingSearch] = []
COUNTRY_PROPERTY: dict[str, str] = {}
COUNTRY_DEALS: dict[str, str] = {
    "GB": "hotukdeals",
    "DE": "mydealz",
    "FR": "dealabs",
    "ES": "chollometro",
    "NL": "peppernl",
    "PL": "pepperpl",
    "MX": "promodescuentos",
    "AT": "preisjaeger",
    "CH": "preispirat",
    "US": "slickdeals",
    "KR": "ppomppu",
    "IT": "dimmicosacerchi",
    "MY": "everydayonsales",
    "AU": "ozbargain",
    "NZ": "cheapies",
    "SG": "singpromos",
}

for _cc, _hl, _cname, _prop_q, _deals_q in _COUNTRY_SEARCHES:
    if _prop_q:
        _sid = f"property-{_cc.lower()}"
        SHOPPING_SEARCHES.append(
            (
                _sid,
                _search_url(_prop_q, _hl, _cc),
                f"Property {_cname}",
                "Property",
                "property",
            )
        )
        COUNTRY_PROPERTY.setdefault(_cc, _sid)
    if _deals_q and _cc not in COUNTRY_DEALS:
        _sid = f"deals-{_cc.lower()}"
        SHOPPING_SEARCHES.append(
            (
                _sid,
                _search_url(_deals_q, _hl, _cc, "14d"),
                f"Deals {_cname}",
                "Deals",
                "deals",
            )
        )
        COUNTRY_DEALS.setdefault(_cc, _sid)

# The visitor country's travel-deals editor, swapped into the deck the same
# way (no generic fallback — the deck already carries a global travel card).
COUNTRY_TRAVEL: dict[str, str] = {
    "GB": "headforpoints",
    "US": "theflightdeal",
    "DE": "urlaubspiraten",
    "FR": "voyagespirates",
    "IT": "piratinviaggio",
    "ES": "viajerospiratas",
    "PL": "wakacyjnipiraci",
    "CH": "ferienpiraten",
    "NL": "vakantiepiraten",
    "BR": "melhoresdestinos",
    "JP": "traicy",
    "KR": "milemoa",
    "DK": "insideflyerdk",
    "NO": "insideflyerno",
    "SE": "insideflyerse",
    "CZ": "zaletsi",
    "GR": "travelgr",
    "AR": "promocionesaereas",
    "VN": "vnexpressdulich",
    "SG": "milelion",
    "IN": "livefromalounge",
    "ZA": "travelstart",
    "AU": "iknowthepilot",
    "NZ": "iknowthepilot",
}

# Direct-feed markets keep their community source as the country pick above;
# the UK/US/… property searches complement (not replace) the direct sources.
COUNTRY_PROPERTY.update(
    {
        "IT": "idealistait",
        "PT": "idealistapt",
        "BR": "loftblog",
        "JP": "realestatejapan",
        "IL": "globesnadlan",
        "TR": "emlaknews",
        "HU": "portfolioingatlan",
        "CZ": "hypoindex",
        "FI": "kiinteistolehti",
        "MY": "edgeprop",
        "VN": "vnexpressbds",
        "PH": "lamudiph",
        "IN": "squareyards",
        "KE": "buyrentkenya",
        "NZ": "interestnz",
        "GB": "propertyindustryeye",
        "US": "realtornews",
        "AU": "realestateau",
        "CA": "storeys",
        "SG": "stackedhomes",
        "ES": "spanishpropertyinsight",
        "FR": "frenchentree",
    }
)


def fallback_search_feeds(
    countries: list[tuple[str, str, str]],
) -> list[ShoppingSearch]:
    """Generated Deals + Property searches for every country edition that has
    neither a community feed nor a hand-localised search, so the seeded deck
    can lead with these categories in ALL markets (English query, local gl).
    Called by ``metadata`` with its COUNTRIES table; mutates the country maps
    so ``endpoints`` sees the fallbacks too."""
    out: list[ShoppingSearch] = []
    for cc, _hl, cname in countries:
        if cc not in COUNTRY_PROPERTY:
            sid = f"property-{cc.lower()}"
            out.append(
                (
                    sid,
                    _search_url(f"{cname} property market", "en", cc, "31d"),
                    f"Property {cname}",
                    "Property",
                    "property",
                )
            )
            COUNTRY_PROPERTY[cc] = sid
        if cc not in COUNTRY_DEALS:
            sid = f"deals-{cc.lower()}"
            out.append(
                (
                    sid,
                    _search_url(f"{cname} deals discounts", "en", cc, "14d"),
                    f"Deals {cname}",
                    "Deals",
                    "deals",
                )
            )
            COUNTRY_DEALS[cc] = sid
    return out


# Localized "what's on" queries for major non-English markets; every other
# country falls back to an English query, which still surfaces that country's
# event coverage via the gl= edition.
_EVENT_QUERIES: dict[str, tuple[str, str]] = {
    "DE": ("de", "Veranstaltungen Konzerte Festivals Spiele"),
    "AT": ("de", "Veranstaltungen Konzerte Österreich"),
    "CH": ("de", "Veranstaltungen Konzerte Schweiz"),
    "FR": ("fr", "événements concerts festivals matchs"),
    "ES": ("es", "eventos conciertos festivales partidos"),
    "IT": ("it", "eventi concerti festival partite"),
    "PT": ("pt-PT", "eventos concertos festivais"),
    "NL": ("nl", "evenementen concerten festivals wedstrijden"),
    "PL": ("pl", "wydarzenia koncerty festiwale mecze"),
    "BR": ("pt-BR", "eventos shows festivais jogos"),
    "MX": ("es-419", "eventos conciertos festivales México"),
    "AR": ("es-419", "eventos recitales festivales Argentina"),
    "JP": ("ja", "イベント コンサート フェス 開催"),
    "KR": ("ko", "행사 콘서트 페스티벌 일정"),
    "TR": ("tr", "etkinlikler konserler festivaller"),
    "GR": ("el", "εκδηλώσεις συναυλίες φεστιβάλ"),
    "SE": ("sv", "evenemang konserter festivaler"),
    "VN": ("vi", "sự kiện hòa nhạc lễ hội"),
    "TH": ("th", "อีเวนต์ คอนเสิร์ต เทศกาล"),
    "ID": ("id", "acara konser festival"),
}

COUNTRY_EVENTS: dict[str, str] = {}


def events_search_feeds(
    countries: list[tuple[str, str, str]],
) -> list[ShoppingSearch]:
    """An "Events {Country}" card for every country edition — upcoming
    concerts/festivals/what's-on coverage, localized where we have a native
    query. Mirrors ``fallback_search_feeds``; mutates ``COUNTRY_EVENTS`` so
    the deck seeding sees the picks."""
    out: list[ShoppingSearch] = []
    for cc, _hl, cname in countries:
        hl, q = _EVENT_QUERIES.get(
            cc, ("en", f"{cname} upcoming events concerts festivals")
        )
        sid = f"events-{cc.lower()}"
        out.append(
            (
                sid,
                _search_url(q, hl, cc, "31d"),
                f"Events {cname}",
                "What's On",
                "entertainment",
            )
        )
        COUNTRY_EVENTS[cc] = sid
    return out


# Six more per-country daily-check families, one generic generator. Each entry:
# (family, kicker, column, glyph_code, recency, en_query_template, localized).
# Localized queries cover the biggest non-English markets; everywhere else the
# English template against the country's own gl= edition still surfaces local
# outlets.
_TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/72x72"

_COUNTRY_CARD_FAMILIES: list[
    tuple[str, str, str, str, str, str, dict[str, tuple[str, str]]]
] = [
    (
        "business",
        "Business",
        "finance",
        "1f4c8",
        "14d",
        "{cname} business economy news",
        {
            "DE": ("de", "Wirtschaft Unternehmen"),
            "AT": ("de", "Wirtschaft Österreich"),
            "CH": ("de", "Wirtschaft Schweiz"),
            "FR": ("fr", "économie entreprises"),
            "ES": ("es", "economía empresas"),
            "IT": ("it", "economia imprese"),
            "BR": ("pt-BR", "economia negócios"),
            "PT": ("pt-PT", "economia empresas"),
            "NL": ("nl", "economie bedrijven"),
            "PL": ("pl", "gospodarka firmy"),
            "JP": ("ja", "経済 企業"),
            "KR": ("ko", "경제 기업"),
            "TR": ("tr", "ekonomi şirketler"),
        },
    ),
    (
        "fuel",
        "Fuel Prices",
        "cars",
        "26fd",
        "7d",
        "{cname} petrol diesel fuel prices",
        {
            "DE": ("de", "Benzinpreis Dieselpreis"),
            "AT": ("de", "Benzinpreis Österreich"),
            "FR": ("fr", "prix carburant essence"),
            "ES": ("es", "precio gasolina diésel"),
            "IT": ("it", "prezzo benzina diesel"),
            "BR": ("pt-BR", "preço gasolina diesel"),
            "NL": ("nl", "benzineprijs diesel"),
            "PL": ("pl", "ceny paliw benzyna"),
            "JP": ("ja", "ガソリン価格"),
            "TR": ("tr", "benzin fiyatı akaryakıt"),
        },
    ),
    (
        "lottery",
        "Lottery",
        "betting",
        "1f3b0",
        "7d",
        "{cname} lottery lotto jackpot results",
        {
            "DE": ("de", "Lotto Jackpot Eurojackpot"),
            "FR": ("fr", "loto EuroMillions résultats"),
            "ES": ("es", "lotería resultados bote"),
            "IT": ("it", "lotto superenalotto estrazione"),
            "BR": ("pt-BR", "loteria mega-sena resultado"),
            "NL": ("nl", "loterij jackpot uitslag"),
            "PL": ("pl", "lotto wyniki kumulacja"),
            "JP": ("ja", "宝くじ 当選"),
            "TR": ("tr", "loto çekiliş sonuçları"),
        },
    ),
    (
        "health",
        "Health",
        "science",
        "1f3e5",
        "14d",
        "{cname} health hospitals news",
        {
            "DE": ("de", "Gesundheit Krankenhäuser"),
            "FR": ("fr", "santé hôpitaux"),
            "ES": ("es", "salud hospitales"),
            "IT": ("it", "sanità ospedali"),
            "BR": ("pt-BR", "saúde hospitais"),
            "NL": ("nl", "gezondheid ziekenhuizen zorg"),
            "PL": ("pl", "zdrowie szpitale"),
            "JP": ("ja", "健康 医療"),
            "KR": ("ko", "건강 의료"),
            "TR": ("tr", "sağlık hastaneler"),
        },
    ),
    (
        "jobs",
        "Jobs",
        "finance",
        "1f4bc",
        "14d",
        "{cname} jobs hiring layoffs",
        {
            "DE": ("de", "Jobs Einstellungen Stellenabbau"),
            "FR": ("fr", "emploi embauches licenciements"),
            "ES": ("es", "empleo contrataciones despidos"),
            "IT": ("it", "lavoro assunzioni licenziamenti"),
            "BR": ("pt-BR", "empregos contratações demissões"),
            "NL": ("nl", "banen vacatures ontslagen"),
            "PL": ("pl", "praca zatrudnienie zwolnienia"),
            "JP": ("ja", "雇用 求人"),
            "TR": ("tr", "istihdam işe alım"),
        },
    ),
    (
        "wxwarn",
        "Weather",
        "news",
        "26c8",
        "7d",
        "{cname} weather warning forecast storm",
        {
            "DE": ("de", "Wetterwarnung Unwetter"),
            "FR": ("fr", "alerte météo tempête"),
            "ES": ("es", "alerta meteorológica tormenta"),
            "IT": ("it", "allerta meteo maltempo"),
            "BR": ("pt-BR", "alerta meteorológico tempestade"),
            "NL": ("nl", "weerswaarschuwing storm"),
            "PL": ("pl", "ostrzeżenie pogodowe burze"),
            "JP": ("ja", "気象警報 天気"),
            "KR": ("ko", "기상 특보 날씨"),
            "TR": ("tr", "hava durumu uyarı fırtına"),
        },
    ),
    (
        "streaming",
        "Streaming",
        "entertainment",
        "1f4fa",
        "7d",
        "new on Netflix Prime Video {cname}",
        {
            "DE": ("de", "neu auf Netflix Prime Video"),
            "FR": ("fr", "nouveautés Netflix Prime Video"),
            "ES": ("es", "estrenos Netflix Prime Video"),
            "IT": ("it", "novità Netflix Prime Video"),
            "BR": ("pt-BR", "lançamentos Netflix Prime Video"),
            "NL": ("nl", "nieuw op Netflix"),
            "PL": ("pl", "nowości Netflix Prime Video"),
            "JP": ("ja", "Netflix 新作 配信"),
            "KR": ("ko", "넷플릭스 신작 공개"),
            "TR": ("tr", "Netflix yeni diziler filmler"),
        },
    ),
    (
        "education",
        "Education",
        "news",
        "1f393",
        "14d",
        "{cname} schools exams education",
        {
            "IN": ("en-IN", "board exam results NEET JEE admission"),
            "NG": ("en-NG", "JAMB WAEC NECO exam results"),
            "KE": ("en-KE", "KCSE KCPE exam results schools"),
            "PH": ("en-PH", "DepEd exam results schools"),
            "IE": ("en-IE", "Leaving Cert schools education"),
            "GB": ("en-GB", "GCSE A-levels schools education"),
            "DE": ("de", "Schule Abitur Prüfungen Bildung"),
            "FR": ("fr", "école bac examens éducation"),
            "ES": ("es", "educación exámenes selectividad"),
            "JP": ("ja", "受験 入試 教育"),
        },
    ),
    (
        "recalls",
        "Recalls",
        "news",
        "26a0",
        "31d",
        "{cname} product recall safety warning",
        {
            "DE": ("de", "Rückruf Produkt Warnung"),
            "FR": ("fr", "rappel produit alerte"),
            "ES": ("es", "retirada producto alerta"),
            "IT": ("it", "richiamo prodotto avviso"),
            "BR": ("pt-BR", "recall produto alerta"),
            "NL": ("nl", "terugroepactie product"),
            "PL": ("pl", "wycofanie produktu ostrzeżenie"),
            "JP": ("ja", "リコール 回収 製品"),
        },
    ),
    (
        "fxrate",
        "Exchange Rate",
        "finance",
        "1f4b1",
        "7d",
        "{cname} currency exchange rate",
        {
            "IN": ("en-IN", "rupee dollar exchange rate"),
            "PH": ("en-PH", "peso dollar exchange rate"),
            "NG": ("en-NG", "naira dollar exchange rate"),
            "TR": ("tr", "dolar euro kuru"),
            "JP": ("ja", "円相場 為替"),
            "BR": ("pt-BR", "dólar hoje cotação"),
            "MX": ("es-419", "tipo de cambio peso dólar"),
            "KR": ("ko", "환율 원달러"),
            "PL": ("pl", "kurs dolara euro złoty"),
            "ID": ("id", "kurs rupiah dolar"),
        },
    ),
    (
        "research",
        "Research",
        "science",
        "1f52c",
        "14d",
        "{cname} science research university discovery",
        {
            "DE": ("de", "Forschung Wissenschaft Universität"),
            "FR": ("fr", "recherche scientifique université"),
            "ES": ("es", "investigación científica universidad"),
            "IT": ("it", "ricerca scientifica università"),
            "BR": ("pt-BR", "pesquisa científica universidade"),
            "NL": ("nl", "wetenschappelijk onderzoek universiteit"),
            "PL": ("pl", "badania naukowe uniwersytet"),
            "JP": ("ja", "研究 科学 大学"),
            "KR": ("ko", "연구 과학 대학"),
            "TR": ("tr", "bilimsel araştırma üniversite"),
        },
    ),
    (
        "ai",
        "AI",
        "tech",
        "1f916",
        "14d",
        "{cname} artificial intelligence AI",
        {
            "DE": ("de", "künstliche Intelligenz KI"),
            "FR": ("fr", "intelligence artificielle IA"),
            "ES": ("es", "inteligencia artificial IA"),
            "IT": ("it", "intelligenza artificiale IA"),
            "BR": ("pt-BR", "inteligência artificial IA"),
            "NL": ("nl", "kunstmatige intelligentie AI"),
            "PL": ("pl", "sztuczna inteligencja AI"),
            "JP": ("ja", "人工知能 AI"),
            "KR": ("ko", "인공지능 AI"),
            "TR": ("tr", "yapay zeka"),
        },
    ),
    (
        "startups",
        "Startups",
        "tech",
        "1f680",
        "14d",
        "{cname} startups funding venture capital",
        {
            "DE": ("de", "Startups Finanzierung Wagniskapital"),
            "FR": ("fr", "startups levée de fonds"),
            "ES": ("es", "startups financiación capital riesgo"),
            "IT": ("it", "startup finanziamenti venture"),
            "BR": ("pt-BR", "startups investimento captação"),
            "NL": ("nl", "startups financiering durfkapitaal"),
            "PL": ("pl", "startupy finansowanie inwestycje"),
            "JP": ("ja", "スタートアップ 資金調達"),
            "KR": ("ko", "스타트업 투자 유치"),
            "TR": ("tr", "girişim yatırım startup"),
        },
    ),
    (
        "climate",
        "Climate",
        "science",
        "1f331",
        "14d",
        "{cname} climate change environment emissions",
        {
            "DE": ("de", "Klimawandel Umwelt Emissionen"),
            "FR": ("fr", "climat environnement émissions"),
            "ES": ("es", "cambio climático medio ambiente"),
            "IT": ("it", "cambiamento climatico ambiente"),
            "BR": ("pt-BR", "mudança climática meio ambiente"),
            "NL": ("nl", "klimaatverandering milieu"),
            "PL": ("pl", "zmiany klimatu środowisko"),
            "JP": ("ja", "気候変動 環境"),
            "KR": ("ko", "기후변화 환경"),
            "TR": ("tr", "iklim değişikliği çevre"),
        },
    ),
    (
        "energy",
        "Energy",
        "science",
        "26a1",
        "14d",
        "{cname} energy renewables electricity power",
        {
            "DE": ("de", "Energie Erneuerbare Strom"),
            "FR": ("fr", "énergie renouvelables électricité"),
            "ES": ("es", "energía renovables electricidad"),
            "IT": ("it", "energia rinnovabili elettricità"),
            "BR": ("pt-BR", "energia renováveis eletricidade"),
            "NL": ("nl", "energie hernieuwbaar elektriciteit"),
            "PL": ("pl", "energia odnawialne prąd"),
            "JP": ("ja", "エネルギー 再生可能 電力"),
            "KR": ("ko", "에너지 재생에너지 전력"),
            "TR": ("tr", "enerji yenilenebilir elektrik"),
        },
    ),
]

COUNTRY_BUSINESS: dict[str, str] = {}
COUNTRY_HEALTH: dict[str, str] = {}

# (source_id, url, name, kicker, column, glyph_url)
CountryCard = tuple[str, str, str, str, str, str]


def country_card_feeds(
    countries: list[tuple[str, str, str]],
) -> list[CountryCard]:
    """Business/Fuel/Lottery/Health/Jobs/Weather-warning cards for every
    country edition. Only Business joins the seeded deck (COUNTRY_BUSINESS);
    the rest are discoverable via the roster."""
    out: list[CountryCard] = []
    for fam, kicker, column, glyph, recency, tmpl, localized in _COUNTRY_CARD_FAMILIES:
        for cc, _hl, cname in countries:
            hl, q = localized.get(cc, ("en", tmpl.format(cname=cname)))
            sid = f"{fam}-{cc.lower()}"
            out.append(
                (
                    sid,
                    _search_url(q, hl, cc, recency),
                    f"{kicker} {cname}",
                    kicker,
                    column,
                    f"{_TWEMOJI_CDN}/{glyph}.png",
                )
            )
            if fam == "business":
                COUNTRY_BUSINESS[cc] = sid
            elif fam == "health":
                COUNTRY_HEALTH[cc] = sid
    return out


# Global daily-ritual cards (one each, not per-country).
GLOBAL_EXTRA_SEARCHES: list[CountryCard] = [
    (
        "horoscope-daily",
        _search_url("daily horoscope zodiac", "en-US", "US", "2d"),
        "Daily Horoscope",
        "Horoscope",
        "culture",
        f"{_TWEMOJI_CDN}/1f52e.png",
    ),
    (
        "royals",
        _search_url("royal family", "en-GB", "GB", "7d"),
        "The Royals",
        "Royals",
        "entertainment",
        f"{_TWEMOJI_CDN}/1f451.png",
    ),
]
