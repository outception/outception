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
        "https://www.cntraveler.com/feed/rss",
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
        "https://www.everydayonsales.com/feed",
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
        "https://www.headlightmag.com/feed",
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
        "travelextra",
        "https://www.travelextra.ie/feed",
        "Travel Extra",
        "travel",
        "https://www.travelextra.ie",
    ),
    (
        "zaletsi",
        "https://www.zaletsi.cz/feed",
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
    "IT": "scontomaggio",
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
    "GB": "holidaypirates",
    "US": "travelpirates",
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
    "IE": "travelextra",
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
