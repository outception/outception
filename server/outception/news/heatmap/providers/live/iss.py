"""The space station's next visible pass over each covered city: the
orbital elements come from the tracking service every six hours and the
passes are propagated on the worker, so every reader is served from the
cache. A pass peaking under ten degrees above the horizon is not listed."""

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sgp4.api import Satrec, jday

from outception.redis import Redis

from ....weather import _CAPITALS
from ...specs import HeatmapSpec
from .. import http
from ._time import countdown_label

TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"
TLE_KEY = "news:heatmap:iss:tle"
TLE_TTL_SECONDS = 6 * 60 * 60
MIN_ELEVATION_DEG = 10.0
LOOKAHEAD_HOURS = 24
STEP_SECONDS = 30
EARTH_RADIUS_KM = 6378.137
FLATTENING = 1 / 298.257223563
TRACK_URL = "https://spotthestation.nasa.gov/"
# Which cities get a pass tile: the top thirty visitor countries' capitals,
# the same table the weather fallback reads.
COVERED_COUNTRIES = (
    "US",
    "GB",
    "IE",
    "CA",
    "AU",
    "NZ",
    "IN",
    "NG",
    "ZA",
    "SG",
    "PH",
    "DE",
    "FR",
    "ES",
    "IT",
    "NL",
    "SE",
    "NO",
    "PL",
    "PT",
    "CH",
    "AT",
    "BE",
    "BR",
    "MX",
    "AR",
    "JP",
    "KR",
    "ID",
    "TR",
)


def _gmst_rad(jd: float) -> float:
    """Greenwich mean sidereal time for a Julian date, in radians."""
    t = (jd - 2451545.0) / 36525.0
    seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    return math.radians((seconds % 86400.0) / 240.0)


def _observer_ecef(lat_deg: float, lon_deg: float) -> tuple[float, float, float]:
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    e2 = FLATTENING * (2 - FLATTENING)
    n = EARTH_RADIUS_KM / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return (
        n * math.cos(lat) * math.cos(lon),
        n * math.cos(lat) * math.sin(lon),
        n * (1 - e2) * math.sin(lat),
    )


def _look_angles(
    sat_teme: tuple[float, float, float],
    jd: float,
    lat_deg: float,
    lon_deg: float,
) -> tuple[float, float]:
    """(elevation, azimuth) in degrees of a satellite position in the
    propagator's inertial frame as seen from a city."""
    theta = _gmst_rad(jd)
    x, y, z = sat_teme
    # Inertial to earth-fixed: rotate by the sidereal angle.
    ex = x * math.cos(theta) + y * math.sin(theta)
    ey = -x * math.sin(theta) + y * math.cos(theta)
    ez = z
    ox, oy, oz = _observer_ecef(lat_deg, lon_deg)
    rx, ry, rz = ex - ox, ey - oy, ez - oz
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    # Earth-fixed to east-north-up at the observer.
    east = -math.sin(lon) * rx + math.cos(lon) * ry
    north = (
        -math.sin(lat) * math.cos(lon) * rx
        - math.sin(lat) * math.sin(lon) * ry
        + math.cos(lat) * rz
    )
    up = (
        math.cos(lat) * math.cos(lon) * rx
        + math.cos(lat) * math.sin(lon) * ry
        + math.sin(lat) * rz
    )
    distance = math.sqrt(east * east + north * north + up * up)
    elevation = math.degrees(math.asin(up / distance)) if distance else -90.0
    azimuth = math.degrees(math.atan2(east, north)) % 360.0
    return elevation, azimuth


def compass(azimuth: float) -> str:
    points = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return points[int((azimuth + 22.5) // 45) % 8]


def next_pass(
    satellite: Satrec,
    lat: float,
    lon: float,
    start: datetime,
    *,
    hours: int = LOOKAHEAD_HOURS,
    step: int = STEP_SECONDS,
) -> dict[str, Any] | None:
    """The first pass after `start` that peaks at or above the minimum
    elevation: its rise time, duration, peak elevation and rise direction."""
    rise: datetime | None = None
    peak = -90.0
    rise_azimuth = 0.0
    steps = hours * 3600 // step
    for i in range(steps):
        moment = start + timedelta(seconds=i * step)
        jd, fr = jday(
            moment.year,
            moment.month,
            moment.day,
            moment.hour,
            moment.minute,
            moment.second + moment.microsecond / 1e6,
        )
        error, position, _ = satellite.sgp4(jd, fr)
        if error != 0:
            continue
        elevation, azimuth = _look_angles(position, jd + fr, lat, lon)
        if elevation > 0:
            if rise is None:
                rise, peak, rise_azimuth = moment, elevation, azimuth
            peak = max(peak, elevation)
        elif rise is not None:
            if peak >= MIN_ELEVATION_DEG:
                return {
                    "rise": rise,
                    "duration_s": int((moment - rise).total_seconds()),
                    "peak": peak,
                    "direction": compass(rise_azimuth),
                }
            rise, peak = None, -90.0
    return None


def tiles_from(
    tle: tuple[str, str],
    cities: list[tuple[str, float, float]],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    satellite = Satrec.twoline2rv(tle[0], tle[1])
    tiles: list[dict[str, Any]] = []
    now_ms_value = int(now.timestamp() * 1000)
    for name, lat, lon in cities:
        found = next_pass(satellite, lat, lon, now)
        if found is None:
            continue
        rise_ms = int(found["rise"].timestamp() * 1000)
        minutes, seconds = divmod(found["duration_s"], 60)
        tiles.append(
            {
                "symbol": name[:14],
                "name": name,
                "changePercent": round(min(3.0, found["peak"] / 30.0), 2),
                "price": round(found["duration_s"] / 60.0, 1),
                "weight": 1.0,
                "label": countdown_label(rise_ms, now_ms_value),
                "subtitle": (
                    f"rises {found['direction']}, peaks {found['peak']:.0f}° above the horizon, "
                    f"{minutes} min {seconds:02d} s"
                ),
                "url": TRACK_URL,
                "_rise": rise_ms,
            }
        )
    tiles.sort(key=lambda tile: tile["_rise"])
    for tile in tiles:
        del tile["_rise"]
    return tiles


def parse_tle(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if (
            line.startswith("1 ")
            and index + 1 < len(lines)
            and lines[index + 1].startswith("2 ")
        ):
            return line, lines[index + 1]
    raise http.NewsFetchError("no orbital elements in the tracking answer")


async def _elements(redis: Redis) -> tuple[str, str]:
    cached = await redis.get(TLE_KEY)
    if cached is not None:
        try:
            line1, line2 = json.loads(cached)
            return str(line1), str(line2)
        except ValueError, TypeError:
            pass
    tle = parse_tle(await http.fetch_text(TLE_URL))
    await redis.set(TLE_KEY, json.dumps(tle), ex=TLE_TTL_SECONDS)
    return tle


def covered_cities() -> list[tuple[str, float, float]]:
    return [_CAPITALS[code] for code in COVERED_COUNTRIES if code in _CAPITALS]


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    return tiles_from(await _elements(redis), covered_cities())
