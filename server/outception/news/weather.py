"""Open-Meteo weather proxy for the wall's weather card.

Keyless and cache-first: the browser sends the reader's coordinates (from
precise geolocation) or, when they decline the permission prompt, their IP
country as a coarse fallback. We proxy Open-Meteo's free forecast API and cache
each rounded location in Redis, so many readers in the same area don't each hit
the upstream (which is generous but rate-limited).
"""

import json
from typing import Any

import structlog

from outception.exceptions import OutceptionError
from outception.redis import Redis

from .fetch import NewsFetchError, fetch_json

log = structlog.get_logger()

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_CACHE_KEY = "news:weather:{lat}:{lon}"
_TTL_SECONDS = 15 * 60  # conditions barely move within 15 minutes
_FORECAST_DAYS = 4

# ISO-3166 country → (capital city, latitude, longitude). The fallback location
# when the reader denies precise geolocation, so the card still shows local
# weather from the IP country alone. Full coverage of UN members and observers
# plus the inhabited territories Cloudflare's CF-IPCountry can emit; ordered by
# code. An unmapped code still falls through to the global default.
_CAPITALS: dict[str, tuple[str, float, float]] = {
    "AD": ("Andorra la Vella", 42.5063, 1.5218),
    "AE": ("Abu Dhabi", 24.4539, 54.3773),
    "AF": ("Kabul", 34.5553, 69.2075),
    "AG": ("Saint John's", 17.1274, -61.8468),
    "AI": ("The Valley", 18.2170, -63.0578),
    "AL": ("Tirana", 41.3275, 19.8187),
    "AM": ("Yerevan", 40.1792, 44.4991),
    "AO": ("Luanda", -8.8390, 13.2894),
    "AR": ("Buenos Aires", -34.6037, -58.3816),
    "AS": ("Pago Pago", -14.2756, -170.7020),
    "AT": ("Vienna", 48.2082, 16.3738),
    "AU": ("Canberra", -35.2809, 149.1300),
    "AW": ("Oranjestad", 12.5240, -70.0270),
    "AX": ("Mariehamn", 60.0973, 19.9348),
    "AZ": ("Baku", 40.4093, 49.8671),
    "BA": ("Sarajevo", 43.8563, 18.4131),
    "BB": ("Bridgetown", 13.1132, -59.5988),
    "BD": ("Dhaka", 23.8103, 90.4125),
    "BE": ("Brussels", 50.8503, 4.3517),
    "BF": ("Ouagadougou", 12.3714, -1.5197),
    "BG": ("Sofia", 42.6977, 23.3219),
    "BH": ("Manama", 26.2285, 50.5860),
    "BI": ("Gitega", -3.4271, 29.9246),
    "BJ": ("Porto-Novo", 6.4969, 2.6289),
    "BL": ("Gustavia", 17.8963, -62.8506),
    "BM": ("Hamilton", 32.2949, -64.7814),
    "BN": ("Bandar Seri Begawan", 4.9031, 114.9398),
    "BO": ("La Paz", -16.4897, -68.1193),
    "BQ": ("Kralendijk", 12.1508, -68.2665),
    "BR": ("Brasília", -15.7939, -47.8828),
    "BS": ("Nassau", 25.0443, -77.3504),
    "BT": ("Thimphu", 27.4712, 89.6339),
    "BW": ("Gaborone", -24.6282, 25.9231),
    "BY": ("Minsk", 53.9006, 27.5590),
    "BZ": ("Belmopan", 17.2514, -88.7705),
    "CA": ("Ottawa", 45.4215, -75.6972),
    "CC": ("West Island", -12.1568, 96.8225),
    "CD": ("Kinshasa", -4.4419, 15.2663),
    "CF": ("Bangui", 4.3947, 18.5582),
    "CG": ("Brazzaville", -4.2634, 15.2429),
    "CH": ("Bern", 46.9480, 7.4474),
    "CI": ("Yamoussoukro", 6.8276, -5.2893),
    "CK": ("Avarua", -21.2129, -159.7773),
    "CL": ("Santiago", -33.4489, -70.6693),
    "CM": ("Yaoundé", 3.8480, 11.5021),
    "CN": ("Beijing", 39.9042, 116.4074),
    "CO": ("Bogotá", 4.7110, -74.0721),
    "CR": ("San José", 9.9281, -84.0907),
    "CU": ("Havana", 23.1136, -82.3666),
    "CV": ("Praia", 14.9330, -23.5133),
    "CW": ("Willemstad", 12.1091, -68.9316),
    "CX": ("Flying Fish Cove", -10.4217, 105.6791),
    "CY": ("Nicosia", 35.1856, 33.3823),
    "CZ": ("Prague", 50.0755, 14.4378),
    "DE": ("Berlin", 52.5200, 13.4050),
    "DJ": ("Djibouti", 11.5721, 43.1456),
    "DK": ("Copenhagen", 55.6761, 12.5683),
    "DM": ("Roseau", 15.3092, -61.3790),
    "DO": ("Santo Domingo", 18.4861, -69.9312),
    "DZ": ("Algiers", 36.7538, 3.0588),
    "EC": ("Quito", -0.1807, -78.4678),
    "EE": ("Tallinn", 59.4370, 24.7536),
    "EG": ("Cairo", 30.0444, 31.2357),
    "EH": ("Laâyoune", 27.1253, -13.1625),
    "ER": ("Asmara", 15.3229, 38.9251),
    "ES": ("Madrid", 40.4168, -3.7038),
    "ET": ("Addis Ababa", 9.0250, 38.7469),
    "FI": ("Helsinki", 60.1699, 24.9384),
    "FJ": ("Suva", -18.1248, 178.4501),
    "FK": ("Stanley", -51.6977, -57.8517),
    "FM": ("Palikir", 6.9248, 158.1610),
    "FO": ("Tórshavn", 62.0079, -6.7908),
    "FR": ("Paris", 48.8566, 2.3522),
    "GA": ("Libreville", 0.4162, 9.4673),
    "GB": ("London", 51.5074, -0.1278),
    "GD": ("Saint George's", 12.0561, -61.7488),
    "GE": ("Tbilisi", 41.7151, 44.8271),
    "GF": ("Cayenne", 4.9224, -52.3135),
    "GG": ("Saint Peter Port", 49.4557, -2.5368),
    "GH": ("Accra", 5.6037, -0.1870),
    "GI": ("Gibraltar", 36.1408, -5.3536),
    "GL": ("Nuuk", 64.1836, -51.7214),
    "GM": ("Banjul", 13.4549, -16.5790),
    "GN": ("Conakry", 9.6412, -13.5784),
    "GP": ("Basse-Terre", 15.9985, -61.7245),
    "GQ": ("Malabo", 3.7523, 8.7742),
    "GR": ("Athens", 37.9838, 23.7275),
    "GT": ("Guatemala City", 14.6349, -90.5069),
    "GU": ("Hagåtña", 13.4745, 144.7504),
    "GW": ("Bissau", 11.8817, -15.6178),
    "GY": ("Georgetown", 6.8013, -58.1551),
    "HK": ("Hong Kong", 22.3193, 114.1694),
    "HN": ("Tegucigalpa", 14.0723, -87.1921),
    "HR": ("Zagreb", 45.8150, 15.9819),
    "HT": ("Port-au-Prince", 18.5944, -72.3074),
    "HU": ("Budapest", 47.4979, 19.0402),
    "ID": ("Jakarta", -6.2088, 106.8456),
    "IE": ("Dublin", 53.3498, -6.2603),
    "IL": ("Jerusalem", 31.7683, 35.2137),
    "IM": ("Douglas", 54.1509, -4.4819),
    "IN": ("New Delhi", 28.6139, 77.2090),
    "IQ": ("Baghdad", 33.3152, 44.3661),
    "IR": ("Tehran", 35.6892, 51.3890),
    "IS": ("Reykjavík", 64.1466, -21.9426),
    "IT": ("Rome", 41.9028, 12.4964),
    "JE": ("Saint Helier", 49.1868, -2.1063),
    "JM": ("Kingston", 17.9714, -76.7931),
    "JO": ("Amman", 31.9454, 35.9284),
    "JP": ("Tokyo", 35.6762, 139.6503),
    "KE": ("Nairobi", -1.2921, 36.8219),
    "KG": ("Bishkek", 42.8746, 74.5698),
    "KH": ("Phnom Penh", 11.5564, 104.9282),
    "KI": ("South Tarawa", 1.3291, 172.9791),
    "KM": ("Moroni", -11.7172, 43.2473),
    "KN": ("Basseterre", 17.3026, -62.7177),
    "KP": ("Pyongyang", 39.0392, 125.7625),
    "KR": ("Seoul", 37.5665, 126.9780),
    "KW": ("Kuwait City", 29.3759, 47.9774),
    "KY": ("George Town", 19.2869, -81.3674),
    "KZ": ("Astana", 51.1694, 71.4491),
    "LA": ("Vientiane", 17.9757, 102.6331),
    "LB": ("Beirut", 33.8938, 35.5018),
    "LC": ("Castries", 14.0101, -60.9875),
    "LI": ("Vaduz", 47.1410, 9.5209),
    "LK": ("Colombo", 6.9271, 79.8612),
    "LR": ("Monrovia", 6.3004, -10.7969),
    "LS": ("Maseru", -29.3151, 27.4869),
    "LT": ("Vilnius", 54.6872, 25.2797),
    "LU": ("Luxembourg", 49.6116, 6.1319),
    "LV": ("Riga", 56.9496, 24.1052),
    "LY": ("Tripoli", 32.8872, 13.1913),
    "MA": ("Rabat", 34.0209, -6.8416),
    "MC": ("Monaco", 43.7384, 7.4246),
    "MD": ("Chișinău", 47.0105, 28.8638),
    "ME": ("Podgorica", 42.4304, 19.2594),
    "MG": ("Antananarivo", -18.8792, 47.5079),
    "MH": ("Majuro", 7.1164, 171.1858),
    "MK": ("Skopje", 41.9981, 21.4254),
    "ML": ("Bamako", 12.6392, -8.0029),
    "MM": ("Naypyidaw", 19.7633, 96.0785),
    "MN": ("Ulaanbaatar", 47.8864, 106.9057),
    "MO": ("Macau", 22.1987, 113.5439),
    "MP": ("Saipan", 15.1778, 145.7503),
    "MQ": ("Fort-de-France", 14.6161, -61.0588),
    "MR": ("Nouakchott", 18.0735, -15.9582),
    "MS": ("Brades", 16.7920, -62.2107),
    "MT": ("Valletta", 35.8989, 14.5146),
    "MU": ("Port Louis", -20.1609, 57.5012),
    "MV": ("Malé", 4.1755, 73.5093),
    "MW": ("Lilongwe", -13.9626, 33.7741),
    "MX": ("Mexico City", 19.4326, -99.1332),
    "MY": ("Kuala Lumpur", 3.1390, 101.6869),
    "MZ": ("Maputo", -25.9692, 32.5732),
    "NA": ("Windhoek", -22.5609, 17.0658),
    "NC": ("Nouméa", -22.2758, 166.4580),
    "NE": ("Niamey", 13.5116, 2.1254),
    "NF": ("Kingston", -29.0569, 167.9617),
    "NG": ("Abuja", 9.0765, 7.3986),
    "NI": ("Managua", 12.1149, -86.2362),
    "NL": ("Amsterdam", 52.3676, 4.9041),
    "NO": ("Oslo", 59.9139, 10.7522),
    "NP": ("Kathmandu", 27.7172, 85.3240),
    "NR": ("Yaren", -0.5477, 166.9209),
    "NU": ("Alofi", -19.0554, -169.9186),
    "NZ": ("Wellington", -41.2865, 174.7762),
    "OM": ("Muscat", 23.5880, 58.3829),
    "PA": ("Panama City", 8.9824, -79.5199),
    "PE": ("Lima", -12.0464, -77.0428),
    "PF": ("Papeete", -17.5516, -149.5585),
    "PG": ("Port Moresby", -9.4438, 147.1803),
    "PH": ("Manila", 14.5995, 120.9842),
    "PK": ("Islamabad", 33.6844, 73.0479),
    "PL": ("Warsaw", 52.2297, 21.0122),
    "PM": ("Saint-Pierre", 46.7784, -56.1773),
    "PN": ("Adamstown", -25.0662, -130.1027),
    "PR": ("San Juan", 18.4655, -66.1057),
    "PS": ("Ramallah", 31.9038, 35.2034),
    "PT": ("Lisbon", 38.7223, -9.1393),
    "PW": ("Ngerulmud", 7.5006, 134.6242),
    "PY": ("Asunción", -25.2637, -57.5759),
    "QA": ("Doha", 25.2854, 51.5310),
    "RE": ("Saint-Denis", -20.8823, 55.4504),
    "RO": ("Bucharest", 44.4268, 26.1025),
    "RS": ("Belgrade", 44.7866, 20.4489),
    "RU": ("Moscow", 55.7558, 37.6173),
    "RW": ("Kigali", -1.9706, 30.1044),
    "SA": ("Riyadh", 24.7136, 46.6753),
    "SB": ("Honiara", -9.4319, 159.9556),
    "SC": ("Victoria", -4.6191, 55.4513),
    "SD": ("Khartoum", 15.5007, 32.5599),
    "SE": ("Stockholm", 59.3293, 18.0686),
    "SG": ("Singapore", 1.3521, 103.8198),
    "SH": ("Jamestown", -15.9387, -5.7168),
    "SI": ("Ljubljana", 46.0569, 14.5058),
    "SK": ("Bratislava", 48.1486, 17.1077),
    "SL": ("Freetown", 8.4657, -13.2317),
    "SM": ("San Marino", 43.9424, 12.4578),
    "SN": ("Dakar", 14.7167, -17.4677),
    "SO": ("Mogadishu", 2.0469, 45.3182),
    "SR": ("Paramaribo", 5.8520, -55.2038),
    "SS": ("Juba", 4.8594, 31.5713),
    "ST": ("São Tomé", 0.3302, 6.7333),
    "SV": ("San Salvador", 13.6929, -89.2182),
    "SX": ("Philipsburg", 18.0255, -63.0450),
    "SY": ("Damascus", 33.5138, 36.2765),
    "SZ": ("Mbabane", -26.3054, 31.1367),
    "TC": ("Cockburn Town", 21.4664, -71.1362),
    "TD": ("N'Djamena", 12.1348, 15.0557),
    "TG": ("Lomé", 6.1725, 1.2314),
    "TH": ("Bangkok", 13.7563, 100.5018),
    "TJ": ("Dushanbe", 38.5598, 68.7870),
    "TK": ("Nukunonu", -9.2005, -171.8484),
    "TL": ("Dili", -8.5569, 125.5603),
    "TM": ("Ashgabat", 37.9601, 58.3261),
    "TN": ("Tunis", 36.8065, 10.1815),
    "TO": ("Nuku'alofa", -21.1393, -175.2049),
    "TR": ("Ankara", 39.9334, 32.8597),
    "TT": ("Port of Spain", 10.6549, -61.5019),
    "TV": ("Funafuti", -8.5211, 179.1962),
    "TW": ("Taipei", 25.0330, 121.5654),
    "TZ": ("Dodoma", -6.1630, 35.7516),
    "UA": ("Kyiv", 50.4501, 30.5234),
    "UG": ("Kampala", 0.3476, 32.5825),
    "US": ("Washington", 38.9072, -77.0369),
    "UY": ("Montevideo", -34.9011, -56.1645),
    "UZ": ("Tashkent", 41.2995, 69.2401),
    "VA": ("Vatican City", 41.9029, 12.4534),
    "VC": ("Kingstown", 13.1587, -61.2248),
    "VE": ("Caracas", 10.4806, -66.9036),
    "VG": ("Road Town", 18.4207, -64.6399),
    "VI": ("Charlotte Amalie", 18.3419, -64.9307),
    "VN": ("Hanoi", 21.0278, 105.8342),
    "VU": ("Port Vila", -17.7333, 168.3273),
    "WF": ("Mata-Utu", -13.2816, -176.1745),
    "WS": ("Apia", -13.8507, -171.7514),
    "XK": ("Pristina", 42.6629, 21.1655),
    "YE": ("Sanaa", 15.3694, 44.1910),
    "YT": ("Mamoudzou", -12.7806, 45.2278),
    "ZA": ("Cape Town", -33.9249, 18.4241),
    "ZM": ("Lusaka", -15.3875, 28.3228),
    "ZW": ("Harare", -17.8252, 31.0335),
}
_DEFAULT: tuple[str, float, float] = ("London", 51.5074, -0.1278)


def resolve_location(
    latitude: float | None,
    longitude: float | None,
    country: str | None,
) -> tuple[str | None, float, float]:
    """Return ``(name, lat, lon)`` for the requested location. Precise
    coordinates win (name is ``None`` — it's filled from the upstream
    timezone); otherwise the IP country's capital; otherwise a global default so
    the card always renders."""
    if latitude is not None and longitude is not None:
        return None, latitude, longitude
    if country:
        capital = _CAPITALS.get(country.strip().upper())
        if capital is not None:
            return capital
    return _DEFAULT


def _timezone_city(timezone: str) -> str:
    """Derive a display name from an IANA timezone: ``Europe/London`` →
    ``London``, ``America/New_York`` → ``New York``."""
    tail = timezone.rsplit("/", 1)[-1]
    return tail.replace("_", " ") or timezone


def _shape(
    location: str, lat: float, lon: float, data: dict[str, Any]
) -> dict[str, Any]:
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    days = daily.get("time") or []
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    return {
        "location": location,
        "latitude": lat,
        "longitude": lon,
        "timezone": data.get("timezone", ""),
        "current": {
            "temperature": current.get("temperature_2m", 0.0),
            "apparent_temperature": current.get("apparent_temperature", 0.0),
            "weather_code": current.get("weather_code", 0),
            "wind_speed": current.get("wind_speed_10m", 0.0),
            "humidity": current.get("relative_humidity_2m", 0),
            "is_day": bool(current.get("is_day", 1)),
        },
        "daily": [
            {
                "date": days[i],
                "weather_code": codes[i] if i < len(codes) else 0,
                "temp_max": highs[i] if i < len(highs) else 0.0,
                "temp_min": lows[i] if i < len(lows) else 0.0,
            }
            for i in range(len(days))
        ],
    }


async def _fetch(lat: float, lon: float) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "is_day,weather_code,wind_speed_10m"
        ),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "forecast_days": _FORECAST_DAYS,
        "wind_speed_unit": "kmh",
    }
    return await fetch_json(_FORECAST_URL, params=params)


async def get_weather(
    redis: Redis,
    latitude: float | None,
    longitude: float | None,
    country: str | None,
) -> dict[str, Any]:
    """Current conditions + a short forecast for the resolved location,
    cache-first. Rounds coordinates to a ~1 km grid so nearby readers share a
    cache entry; raises ``OutceptionError`` (502) only on a cold cache when the
    upstream is unreachable."""
    name, lat, lon = resolve_location(latitude, longitude, country)
    key = _CACHE_KEY.format(lat=round(lat, 2), lon=round(lon, 2))

    cached = await redis.get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except ValueError:
            pass  # malformed entry → treat as a miss

    try:
        data = await _fetch(lat, lon)
    except NewsFetchError as exc:
        log.info("news.weather_failed", lat=lat, lon=lon, error=str(exc))
        raise OutceptionError("Weather is unavailable", status_code=502) from exc

    location = name or _timezone_city(data.get("timezone", ""))
    result = _shape(location, lat, lon, data)
    await redis.set(key, json.dumps(result), ex=_TTL_SECONDS)
    return result
