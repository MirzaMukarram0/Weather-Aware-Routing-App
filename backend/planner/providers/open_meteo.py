from __future__ import annotations

import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
from django.conf import settings
from django.core.cache import cache

from planner.domain.geo import coord_key
from planner.domain.risk import WeatherSample
from planner.providers.errors import ProviderError

OPEN_METEO_TIMEOUT = 45.0
BATCH_CHUNK = 50
EXPECTED_UNITS = {
    "wind_speed_10m": "mph",
    "wind_gusts_10m": "mph",
    "rain": "inch",
    "showers": "inch",
    "snowfall": "inch",
}
_WIND_MPH_ALIASES = frozenset({"mph", "mp/h", "mi/h"})


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_hour_time(value: str) -> datetime:
    return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _unit_matches(var: str, actual: str, expected: str) -> bool:
    if var in ("wind_speed_10m", "wind_gusts_10m") and expected == "mph":
        return actual in _WIND_MPH_ALIASES
    return actual == expected


def _validate_units(hourly_units: dict) -> None:
    for var, expected in EXPECTED_UNITS.items():
        actual = hourly_units.get(var)
        if not _unit_matches(var, actual, expected):
            raise ProviderError(f"Open-Meteo unit for {var} is {actual}, expected {expected}")


def _cache_key(lat: float, lon: float, start: str, end: str) -> str:
    payload = json.dumps([round(lat, 6), round(lon, 6), start, end], sort_keys=True)
    return f"om:{hashlib.sha256(payload.encode()).hexdigest()}"


def _pick_wind_hour(times: list[str], eta: datetime) -> int | None:
    if not times:
        return None
    eta = _as_utc(eta)
    target = eta.replace(minute=0, second=0, microsecond=0)
    if eta - target >= timedelta(minutes=30):
        target += timedelta(hours=1)
    return next((i for i, t in enumerate(times) if _parse_hour_time(t) == target), None)


def _pick_precip_hour(times: list[str], eta: datetime) -> int | None:
    if not times:
        return None
    eta = _as_utc(eta)
    target = eta.replace(minute=0, second=0, microsecond=0)
    if target < eta:
        target += timedelta(hours=1)
    return next((i for i, t in enumerate(times) if _parse_hour_time(t) == target), None)


def fetch_series_for_locations(
    locs: list[tuple[float, float]],
    start_utc: datetime,
    end_utc: datetime,
) -> dict[tuple[float, float], dict]:
    if not locs:
        return {}
    start_s = _as_utc(start_utc).strftime("%Y-%m-%d")
    end_date = min(
        (_as_utc(end_utc) + timedelta(hours=1)).date(),
        datetime.now(UTC).date() + timedelta(days=15),
    )
    end_s = end_date.isoformat()
    out: dict[tuple[float, float], dict] = {}
    missing = []
    for lat, lon in dict.fromkeys(locs):
        cached = cache.get(_cache_key(lat, lon, start_s, end_s))
        if cached is not None:
            out[coord_key(lat, lon)] = cached
        else:
            missing.append((lat, lon))

    def fetch_chunk(chunk):
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
        try:
            with httpx.Client(timeout=OPEN_METEO_TIMEOUT) as client:
                resp = client.get(settings.OPEN_METEO_BASE, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("Weather service unavailable. Please retry shortly.") from exc
        series_list = payload if isinstance(payload, list) else [payload]
        if len(series_list) != len(chunk) or not all(isinstance(s, dict) for s in series_list):
            raise ProviderError("Weather service returned an incomplete batch.")
        result = {}
        for (lat, lon), series in zip(chunk, series_list, strict=True):
            _validate_units(series.get("hourly_units", {}))
            key = coord_key(lat, lon)
            cache.set(_cache_key(lat, lon, start_s, end_s), series, settings.CACHE_TTL_WEATHER)
            result[key] = series
        return result

    chunks = [missing[i : i + BATCH_CHUNK] for i in range(0, len(missing), BATCH_CHUNK)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(fetch_chunk, chunks):
            out.update(result)
    return out


def sample_at_eta(series: dict, eta_utc: datetime) -> WeatherSample:
    hourly = series.get("hourly") or {}
    times = hourly.get("time") or []
    wi = _pick_wind_hour(times, eta_utc)
    pi = _pick_precip_hour(times, eta_utc)

    def val(field: str, idx: int | None) -> float | None:
        if idx is None:
            return None
        arr = hourly.get(field) or []
        if idx >= len(arr):
            return None
        v = arr[idx]
        if v is None:
            return None
        try:
            value = float(v)
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) and value >= 0 else None

    rain = None
    if pi is not None:
        r = val("rain", pi)
        s = val("showers", pi)
        if r is not None and s is not None:
            rain = r + s

    return WeatherSample(
        wind_sustained_mph=val("wind_speed_10m", wi),
        wind_gust_mph=val("wind_gusts_10m", wi),
        rain_in_hr=rain,
        snow_in_hr=val("snowfall", pi),
    )


def batch_samples(
    coords: list[tuple[float, float, datetime]],
) -> dict[tuple[float, float, datetime], WeatherSample]:
    if not coords:
        return {}
    start = min(c[2] for c in coords)
    end = max(c[2] for c in coords)
    unique_locs = list({coord_key(lat, lon) for lat, lon, _ in coords})
    series_by_loc = fetch_series_for_locations(unique_locs, start, end)

    out: dict[tuple[float, float, datetime], WeatherSample] = {}
    for lat, lon, eta in coords:
        ck = coord_key(lat, lon)
        series = series_by_loc.get(ck)
        if series is None:
            out[(lat, lon, eta)] = WeatherSample(None, None, None, None)
        else:
            out[(lat, lon, eta)] = sample_at_eta(series, eta)
    return out
