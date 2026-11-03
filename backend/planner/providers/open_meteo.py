from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import httpx
from django.conf import settings
from django.core.cache import cache

from planner.domain.risk import WeatherSample
from planner.providers.here import ProviderError

OPEN_METEO_TIMEOUT = 45.0
EXPECTED_UNITS = {
    "wind_speed_10m": "mph",
    "wind_gusts_10m": "mph",
    "rain": "inch",
    "showers": "inch",
    "snowfall": "inch",
}


def _cache_key(lat: float, lon: float, start: str, end: str) -> str:
    payload = json.dumps([round(lat, 6), round(lon, 6), start, end], sort_keys=True)
    return f"om:{hashlib.sha256(payload.encode()).hexdigest()}"


def _pick_wind_hour(times: list[str], eta: datetime) -> int | None:
    if not times:
        return None
    eta = eta.astimezone(UTC)
    best_idx = None
    best_delta = None
    for i, t in enumerate(times):
        ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
        delta = abs((ts - eta).total_seconds())
        if best_delta is None or delta < best_delta or (delta == best_delta and i > best_idx):
            best_delta = delta
            best_idx = i
    return best_idx


def _pick_precip_hour(times: list[str], eta: datetime) -> int | None:
    if not times:
        return None
    eta = eta.astimezone(UTC)
    chosen = None
    for i, t in enumerate(times):
        ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if ts >= eta:
            chosen = i
            break
    if chosen is None:
        return None
    return chosen


def _validate_units(hourly_units: dict) -> None:
    for var, expected in EXPECTED_UNITS.items():
        actual = hourly_units.get(var)
        if actual and actual != expected:
            raise ProviderError(f"Open-Meteo unit for {var} is {actual}, expected {expected}")


def fetch_hourly_series(lat: float, lon: float, start_utc: datetime, end_utc: datetime) -> dict:
    start_s = start_utc.astimezone(UTC).strftime("%Y-%m-%d")
    end_s = end_utc.astimezone(UTC).strftime("%Y-%m-%d")
    key = _cache_key(lat, lon, start_s, end_s)
    cached = cache.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
        "start_date": start_s,
        "end_date": end_s,
    }
    with httpx.Client(timeout=OPEN_METEO_TIMEOUT) as client:
        resp = client.get(settings.OPEN_METEO_BASE, params=params)
        if resp.status_code >= 400:
            raise ProviderError(f"Open-Meteo error {resp.status_code}")
        data = resp.json()

    _validate_units(data.get("hourly_units", {}))
    cache.set(key, data, settings.CACHE_TTL_WEATHER)
    return data


def sample_at_eta(series: dict, eta_utc: datetime) -> WeatherSample:
    hourly = series.get("hourly") or {}
    times = hourly.get("time") or []
    wi = _pick_wind_hour(times, eta_utc)
    pi = _pick_precip_hour(times, eta_utc)

    def val(key: str, idx: int | None) -> float | None:
        if idx is None:
            return None
        arr = hourly.get(key) or []
        if idx >= len(arr):
            return None
        v = arr[idx]
        if v is None:
            return None
        return float(v)

    rain = None
    if pi is not None:
        r = val("rain", pi)
        s = val("showers", pi)
        if r is not None or s is not None:
            rain = (r or 0.0) + (s or 0.0)

    return WeatherSample(
        wind_sustained_mph=val("wind_speed_10m", wi),
        wind_gust_mph=val("wind_gusts_10m", wi),
        rain_in_hr=rain,
        snow_in_hr=val("snowfall", pi),
    )


def batch_samples(
    coords: list[tuple[float, float, datetime]],
) -> dict[tuple[float, float], WeatherSample]:
    if not coords:
        return {}
    min_eta = min(c[2] for c in coords)
    max_eta = max(c[2] for c in coords)
    start = min_eta
    end = max_eta

    unique_locs = {(round(lat, 6), round(lon, 6)) for lat, lon, _ in coords}
    series_by_loc: dict[tuple[float, float], dict] = {}
    for lat, lon in unique_locs:
        series_by_loc[(lat, lon)] = fetch_hourly_series(lat, lon, start, end)

    out: dict[tuple[float, float], WeatherSample] = {}
    for lat, lon, eta in coords:
        loc = (round(lat, 6), round(lon, 6))
        out[(lat, lon)] = sample_at_eta(series_by_loc[loc], eta)
    return out
