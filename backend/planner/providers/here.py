from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

HERE_TIMEOUT = 30.0
MAX_RETRIES = 1


class ProviderError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def _cache_get(key: str) -> Any | None:
    return cache.get(key)


def _cache_set(key: str, value: Any, ttl: int) -> None:
    cache.set(key, value, ttl)


def _request(method: str, url: str, **kwargs) -> dict | list:
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=HERE_TIMEOUT) as client:
                resp = client.request(method, url, **kwargs)
                if resp.status_code >= 400:
                    raise ProviderError(f"HERE error {resp.status_code}", resp.status_code)
                return resp.json()
        except (httpx.HTTPError, ProviderError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                continue
            raise ProviderError("HERE request failed") from last_err
    raise ProviderError("HERE request failed")


def autosuggest(query: str, limit: int = 8) -> list[dict]:
    if not query.strip():
        return []
    key = f"here:geo:{hashlib.sha256(query.strip().lower().encode()).hexdigest()}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    api_key = settings.HERE_API_KEY
    if not api_key:
        raise ProviderError("HERE_API_KEY not configured")

    url = "https://autosuggest.search.hereapi.com/v1/autosuggest"
    params = {"q": query, "apiKey": api_key, "limit": limit, "in": "countryCode:USA"}
    data = _request("GET", url, params=params)
    items = []
    for item in data.get("items", []):
        pos = item.get("position") or {}
        if "lat" not in pos or "lng" not in pos:
            continue
        items.append(
            {
                "id": item.get("id") or item.get("title", ""),
                "label": item.get("title", ""),
                "lat": pos["lat"],
                "lon": pos["lng"],
            }
        )
    _cache_set(key, items, settings.CACHE_TTL_GEO)
    return items


def _route_key(
    origin: tuple[float, float],
    dest: tuple[float, float],
    weight_kg: float,
    via: tuple[float, float] | None,
) -> str:
    payload = json.dumps([origin, dest, weight_kg, via], sort_keys=True)
    return f"here:route:{hashlib.sha256(payload.encode()).hexdigest()}"


def _parse_route(route: dict) -> dict | None:
    sections = route.get("sections") or []
    if not sections:
        return None
    poly_parts = []
    total_length = 0.0
    total_duration = 0.0
    parsed_sections = []
    for sec in sections:
        if sec.get("type") != "vehicle":
            continue
        poly = sec.get("polyline") or sec.get("departure", {}).get("place", {}).get("location")
        if isinstance(poly, str):
            poly_parts.append(poly)
        total_length += float(sec.get("summary", {}).get("length", 0))
        total_duration += float(sec.get("summary", {}).get("duration", 0))
        parsed_sections.append(
            {
                "length_m": float(sec.get("summary", {}).get("length", 0)),
                "duration_s": float(sec.get("summary", {}).get("duration", 0)),
            }
        )
    if not poly_parts:
        return None
    return {
        "polyline": poly_parts[0] if len(poly_parts) == 1 else poly_parts[0],
        "length_m": total_length,
        "duration_s": total_duration,
        "sections": parsed_sections,
    }


def _fetch_routes(
    origin: tuple[float, float],
    dest: tuple[float, float],
    weight_kg: float,
    via: tuple[float, float] | None = None,
) -> list[dict]:
    api_key = settings.HERE_API_KEY
    if not api_key:
        raise ProviderError("HERE_API_KEY not configured")

    url = "https://router.hereapi.com/v8/routes"
    origin_param = f"{origin[0]},{origin[1]}"
    dest_param = f"{dest[0]},{dest[1]}"
    params: dict = {
        "apiKey": api_key,
        "transportMode": "truck",
        "origin": origin_param,
        "destination": dest_param,
        "return": "polyline,summary,travelSummary",
        "alternatives": 2,
        "vehicle[grossWeight]": int(weight_kg),
    }
    if via:
        params["via"] = f"{via[0]},{via[1]}"

    data = _request("GET", url, params=params)
    routes = []
    for r in data.get("routes", []):
        parsed = _parse_route(r)
        if parsed:
            routes.append(parsed)
    return routes


def _geometry_key(polyline: str) -> str:
    return hashlib.sha256(polyline.encode()).hexdigest()[:16]


def truck_routes(
    origin: tuple[float, float],
    dest: tuple[float, float],
    weight_lb: float,
) -> tuple[list[dict], list[str]]:
    weight_kg = weight_lb * 0.45359237
    cache_key = _route_key(origin, dest, weight_kg, None)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    warnings: list[str] = []
    routes = _fetch_routes(origin, dest, weight_kg)
    seen = set()
    unique: list[dict] = []
    for r in routes:
        gk = _geometry_key(r["polyline"])
        if gk in seen:
            continue
        seen.add(gk)
        unique.append(r)

    if len(unique) < 3:
        mid_lat = (origin[0] + dest[0]) / 2 + 0.15
        mid_lon = (origin[1] + dest[1]) / 2 - 0.15
        extra = _fetch_routes(origin, dest, weight_kg, via=(mid_lat, mid_lon))
        for r in extra:
            gk = _geometry_key(r["polyline"])
            if gk in seen:
                continue
            seen.add(gk)
            unique.append(r)

    if len(unique) < 3:
        warnings.append(
            f"HERE returned {len(unique)} distinct truck route(s); "
            "fewer than 3 alternatives available."
        )

    result = (unique[:3], warnings)
    _cache_set(cache_key, result, settings.CACHE_TTL_ROUTE)
    return result
