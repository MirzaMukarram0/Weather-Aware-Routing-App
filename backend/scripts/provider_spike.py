"""Optional live provider check. Requires HERE_API_KEY in env."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import UTC, datetime, timedelta  # noqa: E402

from planner.providers.here import truck_routes  # noqa: E402
from planner.providers.open_meteo import fetch_hourly_series  # noqa: E402

TRIPS = [
    ((41.8781, -87.6298), (39.7392, -104.9903), "Chicago → Denver"),
    ((33.7490, -84.3880), (32.7767, -96.7970), "Atlanta → Dallas"),
]


def main() -> int:
    if not os.environ.get("HERE_API_KEY"):
        print("Skip: HERE_API_KEY not set")
        return 0
    for origin, dest, label in TRIPS:
        routes, warnings = truck_routes(origin, dest, 25_000)
        print(f"{label}: {len(routes)} route(s)", warnings)
    now = datetime.now(UTC)
    data = fetch_hourly_series(40.0, -75.0, now, now + timedelta(hours=48))
    hourly = data.get("hourly", {})
    assert "wind_speed_10m" in hourly
    print("Open-Meteo OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
