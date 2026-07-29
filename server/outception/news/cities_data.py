"""Local-news feeds for the biggest cities in each country — Google News search
per city. Same feed shape as ``life_data`` so it reuses the same getters and
``SOURCES`` generation. Column ``cities``; the city is the card title and the
country is the kicker. Plain data (no ``news`` imports).
"""

from __future__ import annotations

import re

Feed = tuple[str, str, str, str, str]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _q(text: str) -> str:
    return re.sub(r"\s+", "+", text.strip())


# country -> its biggest cities (roughly top 4 by population).
_CITIES: dict[str, list[str]] = {
    "United States": ["New York", "Los Angeles", "Chicago", "Houston"],
    "United Kingdom": ["London", "Birmingham", "Manchester", "Glasgow"],
    "Ireland": ["Dublin", "Cork", "Limerick", "Galway"],
    "Canada": ["Toronto", "Montreal", "Vancouver", "Calgary"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth"],
    "New Zealand": ["Auckland", "Wellington", "Christchurch", "Hamilton"],
    "India": ["Mumbai", "Delhi", "Bangalore", "Kolkata"],
    "China": ["Shanghai", "Beijing", "Guangzhou", "Shenzhen"],
    "Japan": ["Tokyo", "Osaka", "Yokohama", "Nagoya"],
    "South Korea": ["Seoul", "Busan", "Incheon", "Daegu"],
    "Germany": ["Berlin", "Hamburg", "Munich", "Cologne"],
    "France": ["Paris", "Marseille", "Lyon", "Toulouse"],
    "Italy": ["Rome", "Milan", "Naples", "Turin"],
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville"],
    "Portugal": ["Lisbon", "Porto", "Braga", "Coimbra"],
    "Netherlands": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht"],
    "Belgium": ["Brussels", "Antwerp", "Ghent", "Bruges"],
    "Switzerland": ["Zurich", "Geneva", "Basel", "Bern"],
    "Austria": ["Vienna", "Graz", "Linz", "Salzburg"],
    "Sweden": ["Stockholm", "Gothenburg", "Malmo", "Uppsala"],
    "Norway": ["Oslo", "Bergen", "Trondheim", "Stavanger"],
    "Denmark": ["Copenhagen", "Aarhus", "Odense", "Aalborg"],
    "Finland": ["Helsinki", "Espoo", "Tampere", "Vantaa"],
    "Poland": ["Warsaw", "Krakow", "Lodz", "Wroclaw"],
    "Czech Republic": ["Prague", "Brno", "Ostrava", "Plzen"],
    "Hungary": ["Budapest", "Debrecen", "Szeged", "Miskolc"],
    "Romania": ["Bucharest", "Cluj-Napoca", "Timisoara", "Iasi"],
    "Greece": ["Athens", "Thessaloniki", "Patras", "Heraklion"],
    "Turkey": ["Istanbul", "Ankara", "Izmir", "Bursa"],
    "Russia": ["Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg"],
    "Ukraine": ["Kyiv", "Kharkiv", "Odesa", "Lviv"],
    "Croatia": ["Zagreb", "Split", "Rijeka", "Osijek"],
    "Serbia": ["Belgrade", "Novi Sad", "Nis", "Kragujevac"],
    "Bulgaria": ["Sofia", "Plovdiv", "Varna", "Burgas"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Salvador"],
    "Mexico": ["Mexico City", "Guadalajara", "Monterrey", "Puebla"],
    "Argentina": ["Buenos Aires", "Cordoba", "Rosario", "Mendoza"],
    "Colombia": ["Bogota", "Medellin", "Cali", "Barranquilla"],
    "Chile": ["Santiago", "Valparaiso", "Concepcion", "Antofagasta"],
    "Peru": ["Lima", "Arequipa", "Trujillo", "Chiclayo"],
    "Venezuela": ["Caracas", "Maracaibo", "Valencia Venezuela", "Barquisimeto"],
    "Ecuador": ["Quito", "Guayaquil", "Cuenca", "Ambato"],
    "Egypt": ["Cairo", "Alexandria", "Giza", "Luxor"],
    "Nigeria": ["Lagos", "Kano", "Ibadan", "Abuja"],
    "South Africa": ["Johannesburg", "Cape Town", "Durban", "Pretoria"],
    "Kenya": ["Nairobi", "Mombasa", "Kisumu", "Nakuru"],
    "Morocco": ["Casablanca", "Rabat", "Marrakesh", "Fez"],
    "Algeria": ["Algiers", "Oran", "Constantine", "Annaba"],
    "Tunisia": ["Tunis", "Sfax", "Sousse", "Kairouan"],
    "Ghana": ["Accra", "Kumasi", "Tamale", "Takoradi"],
    "Ethiopia": ["Addis Ababa", "Dire Dawa", "Mekelle", "Gondar"],
    "Tanzania": ["Dar es Salaam", "Dodoma", "Mwanza", "Arusha"],
    "Saudi Arabia": ["Riyadh", "Jeddah", "Mecca", "Medina"],
    "United Arab Emirates": ["Dubai", "Abu Dhabi", "Sharjah", "Al Ain"],
    "Qatar": ["Doha", "Al Rayyan", "Al Wakrah", "Lusail"],
    "Israel": ["Jerusalem", "Tel Aviv", "Haifa", "Beersheba"],
    "Iran": ["Tehran", "Mashhad", "Isfahan", "Shiraz"],
    "Iraq": ["Baghdad", "Basra", "Mosul", "Erbil"],
    "Pakistan": ["Karachi", "Lahore", "Islamabad", "Faisalabad"],
    "Bangladesh": ["Dhaka", "Chittagong", "Khulna", "Sylhet"],
    "Sri Lanka": ["Colombo", "Kandy", "Galle", "Jaffna"],
    "Indonesia": ["Jakarta", "Surabaya", "Bandung", "Medan"],
    "Malaysia": ["Kuala Lumpur", "George Town", "Johor Bahru", "Ipoh"],
    "Singapore": ["Singapore city", "Jurong", "Woodlands", "Tampines"],
    "Thailand": ["Bangkok", "Chiang Mai", "Phuket", "Pattaya"],
    "Vietnam": ["Ho Chi Minh City", "Hanoi", "Da Nang", "Hai Phong"],
    "Philippines": ["Manila", "Quezon City", "Cebu City", "Davao"],
    "Taiwan": ["Taipei", "Kaohsiung", "Taichung", "Tainan"],
    "Hong Kong": ["Hong Kong city", "Kowloon", "Tsuen Wan", "Sha Tin"],
}


# ISO-3166 alpha-2 for each country above, so the default deck can add the
# visitor's biggest-city local feed by their IP country.
_ISO: dict[str, str] = {
    "United States": "US",
    "United Kingdom": "GB",
    "Ireland": "IE",
    "Canada": "CA",
    "Australia": "AU",
    "New Zealand": "NZ",
    "India": "IN",
    "China": "CN",
    "Japan": "JP",
    "South Korea": "KR",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Portugal": "PT",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Switzerland": "CH",
    "Austria": "AT",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Finland": "FI",
    "Poland": "PL",
    "Czech Republic": "CZ",
    "Hungary": "HU",
    "Romania": "RO",
    "Greece": "GR",
    "Turkey": "TR",
    "Russia": "RU",
    "Ukraine": "UA",
    "Croatia": "HR",
    "Serbia": "RS",
    "Bulgaria": "BG",
    "Brazil": "BR",
    "Mexico": "MX",
    "Argentina": "AR",
    "Colombia": "CO",
    "Chile": "CL",
    "Peru": "PE",
    "Venezuela": "VE",
    "Ecuador": "EC",
    "Egypt": "EG",
    "Nigeria": "NG",
    "South Africa": "ZA",
    "Kenya": "KE",
    "Morocco": "MA",
    "Algeria": "DZ",
    "Tunisia": "TN",
    "Ghana": "GH",
    "Ethiopia": "ET",
    "Tanzania": "TZ",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "Qatar": "QA",
    "Israel": "IL",
    "Iran": "IR",
    "Iraq": "IQ",
    "Pakistan": "PK",
    "Bangladesh": "BD",
    "Sri Lanka": "LK",
    "Indonesia": "ID",
    "Malaysia": "MY",
    "Singapore": "SG",
    "Thailand": "TH",
    "Vietnam": "VN",
    "Philippines": "PH",
    "Taiwan": "TW",
    "Hong Kong": "HK",
}

# ISO2 -> that country's biggest-city local feed id.
COUNTRY_TOP_CITY: dict[str, str] = {
    _ISO[name]: f"city-{_slug(name)}-{_slug(cities[0])}"
    for name, cities in _CITIES.items()
    if name in _ISO
}


def _build() -> list[Feed]:
    feeds: list[Feed] = []
    seen: set[str] = set()
    for country, cities in _CITIES.items():
        for city in cities:
            sid = f"city-{_slug(country)}-{_slug(city)}"
            if sid in seen:
                continue
            seen.add(sid)
            query = _q(f"{city} local news")
            feeds.append((query, sid, city, country, "cities"))
    return feeds


CITY_FEEDS: list[Feed] = _build()
