"""Service alerts for one city's transit network, one adapter per agency
behind one contract: `parse(payload) -> tiles`. Two feed shapes exist:
the London line-status JSON and the GTFS-realtime alerts protobuf the
other agencies publish. Registration keys live only in the environment.
An empty alert list is a real answer: the card carries no tiles and hides
itself."""

from dataclasses import dataclass
from typing import Any, Protocol

from google.transit import gtfs_realtime_pb2

from outception.config import settings
from outception.redis import Redis

from ...specs import HeatmapSpec
from .. import http
from ._time import age_label, now_ms

LIMIT = 24


class TransitAdapter(Protocol):
    def parse(
        self, payload: bytes | dict[str, Any] | list[Any]
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class Agency:
    city: str
    url: str
    adapter: TransitAdapter
    # The settings field holding the registration key, when the agency
    # needs one, and the header it travels in.
    key_field: str | None = None
    key_header: str = "x-api-key"
    key_prefix: str = ""
    binary: bool = False


class LineStatusAdapter:
    """The London line-status answer: every line with its current status;
    good service is severity 10 and carries no alert."""

    GOOD_SERVICE = 10

    def parse(
        self, payload: bytes | dict[str, Any] | list[Any]
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            return []
        tiles: list[dict[str, Any]] = []
        for line in payload:
            if not isinstance(line, dict):
                continue
            name = str(line.get("name") or "")
            for status in line.get("lineStatuses") or []:
                severity = int(status.get("statusSeverity") or self.GOOD_SERVICE)
                if severity == self.GOOD_SERVICE or not name:
                    continue
                description = str(
                    status.get("statusSeverityDescription") or "Disruption"
                )
                reason = " ".join(str(status.get("reason") or "").split())
                reason = reason.removeprefix(f"{name}: ").removeprefix(f"{name} Line: ")
                # Lower severity numbers are worse in this feed.
                heat = -3.0 if severity <= 4 else -1.8 if severity <= 7 else -0.8
                tiles.append(
                    {
                        "symbol": name[:14],
                        "name": description,
                        "changePercent": heat,
                        "price": float(self.GOOD_SERVICE - severity),
                        "weight": 1.0,
                        "label": name,
                        "subtitle": reason[:160] or None,
                        "url": "https://tfl.gov.uk/tube-dlr-overground/status/",
                    }
                )
        tiles.sort(key=lambda tile: -tile["price"])
        return tiles[:LIMIT]


class GtfsAlertsAdapter:
    """GTFS-realtime service alerts: one tile per active alert, the
    affected routes as the subtitle, severity as colour."""

    def __init__(self, home_url: str) -> None:
        self.home_url = home_url

    def parse(
        self, payload: bytes | dict[str, Any] | list[Any]
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, bytes):
            return []
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(payload)
        now = now_ms()
        tiles: list[dict[str, Any]] = []
        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            alert = entity.alert
            header = _translation(alert.header_text)
            if not header:
                continue
            routes = sorted(
                {
                    selector.route_id
                    for selector in alert.informed_entity
                    if selector.route_id
                }
            )
            active = True
            start_ms: int | None = None
            for period in alert.active_period:
                if period.HasField("start"):
                    start_ms = period.start * 1000
                    if start_ms > now:
                        active = False
                if period.HasField("end") and period.end * 1000 < now:
                    active = False
            if not active:
                continue
            severity = getattr(alert, "severity_level", 0)
            heat = -3.0 if severity >= 4 else -1.8 if severity == 3 else -0.8
            tiles.append(
                {
                    "symbol": (
                        routes[0] if len(routes) == 1 else f"{len(routes)} lines"
                    )[:14]
                    if routes
                    else "Network",
                    "name": header[:120],
                    "changePercent": heat,
                    "price": float(severity),
                    "weight": 1.0,
                    "label": age_label(start_ms, now) if start_ms else "ongoing",
                    "subtitle": ", ".join(routes)[:160] or None,
                    "url": _translation(alert.url) or self.home_url,
                    "_start": start_ms or 0,
                }
            )
        tiles.sort(key=lambda tile: (-tile["price"], -tile["_start"]))
        for tile in tiles:
            del tile["_start"]
        return tiles[:LIMIT]


def _translation(field: Any) -> str:
    translations = list(getattr(field, "translation", []))
    if not translations:
        return ""
    english = next(
        (t.text for t in translations if t.language in ("en", "", "en-US")), None
    )
    return " ".join(str(english or translations[0].text).split())


# The first five cities. Every feed is verified against the live agency
# before the signal is switched on; until then the rows stay disabled.
AGENCIES: dict[str, Agency] = {
    "london": Agency(
        city="london",
        url="https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground,elizabeth-line,tram/Status",
        adapter=LineStatusAdapter(),
    ),
    "newyork": Agency(
        city="newyork",
        url="https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts",
        adapter=GtfsAlertsAdapter("https://new.mta.info/alerts"),
        key_field="TRANSIT_KEY_NEWYORK",
        binary=True,
    ),
    "dublin": Agency(
        city="dublin",
        url="https://api.nationaltransport.ie/gtfsr/v2/gtfsr",
        adapter=GtfsAlertsAdapter("https://www.transportforireland.ie/"),
        key_field="TRANSIT_KEY_DUBLIN",
        binary=True,
    ),
    "sydney": Agency(
        city="sydney",
        url="https://api.transport.nsw.gov.au/v2/gtfs/alerts/sydneytrains",
        adapter=GtfsAlertsAdapter("https://transportnsw.info/alerts"),
        key_field="TRANSIT_KEY_SYDNEY",
        key_header="Authorization",
        key_prefix="apikey ",
        binary=True,
    ),
    "toronto": Agency(
        city="toronto",
        url="https://bustime.ttc.ca/gtfsrt/alerts",
        adapter=GtfsAlertsAdapter("https://www.ttc.ca/service-alerts"),
        binary=True,
    ),
}


def agency_for(spec: HeatmapSpec) -> Agency:
    try:
        return AGENCIES[spec.code]
    except KeyError as e:
        raise http.NewsFetchError(f"no transit agency for {spec.code!r}") from e


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    agency = agency_for(spec)
    headers: dict[str, str] | None = None
    if agency.key_field:
        key = getattr(settings, agency.key_field, None)
        if not key:
            raise http.NewsFetchError(f"transit {agency.city}: no registration key")
        headers = {agency.key_header: f"{agency.key_prefix}{key}"}
    if agency.binary:
        payload: bytes | dict[str, Any] | list[Any] = await http.fetch_bytes(
            agency.url, headers=headers
        )
    else:
        payload = await http.fetch_json(agency.url, headers=headers)
    return agency.adapter.parse(payload)
