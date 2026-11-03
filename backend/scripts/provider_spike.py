"""Optional live provider check. No API keys required."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import UTC, datetime, timedelta  # noqa: E402

from planner.domain.geo import coord_key  # noqa: E402
from planner.providers.nominatim import autosuggest  # noqa: E402
from planner.providers.open_meteo import fetch_series_for_locations  # noqa: E402
from planner.providers.osrm import truck_routes  # noqa: E402

TRIPS = [
    ((41.8781, -87.6298), (39.7392, -104.9903), "Chicago → Denver"),
    ((33.7490, -84.3880), (32.7767, -96.7970), "Atlanta → Dallas"),
]


def main() -> int:
    places = autosuggest("Chicago, IL")
    print(f"Nominatim: {len(places)} result(s) for Chicago")
    for origin, dest, label in TRIPS:
        routes, warnings = truck_routes(origin, dest)
        print(f"{label}: {len(routes)} route(s)", warnings)
    now = datetime.now(UTC)
    loc = coord_key(40.0, -75.0)
    batch = fetch_series_for_locations([loc], now, now + timedelta(hours=48))
    data = batch[loc]
    hourly = data.get("hourly", {})
    assert "wind_speed_10m" in hourly
    print("Open-Meteo OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
