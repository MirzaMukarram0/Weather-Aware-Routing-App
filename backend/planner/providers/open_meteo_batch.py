"""Batch Open-Meteo requests for many coordinates (chunked)."""

from __future__ import annotations

from datetime import datetime

import httpx
from django.conf import settings

from planner.providers.here import ProviderError
from planner.providers.open_meteo import _validate_units

CHUNK = 50


def batch_series_for_locations(
    locs: list[tuple[float, float]],
    start_utc: datetime,
    end_utc: datetime,
) -> dict[tuple[float, float], dict]:
    if not locs:
        return {}
    start_s = start_utc.strftime("%Y-%m-%d")
    end_s = end_utc.strftime("%Y-%m-%d")
    out: dict[tuple[float, float], dict] = {}
    for i in range(0, len(locs), CHUNK):
        chunk = locs[i : i + CHUNK]
        lats = ",".join(str(lat) for lat, _ in chunk)
        lons = ",".join(str(lon) for _, lon in chunk)
        params = {
            "latitude": lats,
            "longitude": lons,
            "hourly": "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_date": start_s,
            "end_date": end_s,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.get(settings.OPEN_METEO_BASE, params=params)
            if resp.status_code >= 400:
                raise ProviderError(f"Open-Meteo batch error {resp.status_code}")
            payload = resp.json()
        if isinstance(payload, list):
            series_list = payload
        else:
            series_list = [payload]
        for (lat, lon), series in zip(chunk, series_list, strict=False):
            _validate_units(series.get("hourly_units", {}))
            out[(lat, lon)] = series
    return out
