"""Routing via OSRM (open source, public demo server — no API key)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from planner.providers.errors import ProviderError

OSRM_TIMEOUT = 45.0


def _request(url: str, params: dict) -> dict:
    try:
        with httpx.Client(timeout=OSRM_TIMEOUT) as client:
            resp = client.get(url, params=params)
            if resp.status_code >= 400:
                raise ProviderError(f"Routing service unavailable ({resp.status_code}).")
            data = resp.json()
            if data.get("code") != "Ok":
                raise ProviderError(data.get("message", "OSRM routing failed"))
            return data
    except (httpx.HTTPError, ValueError) as e:
        raise ProviderError("OSRM request failed") from e


def _route_key(
    origin: tuple[float, float],
    dest: tuple[float, float],
    via: tuple[float, float] | None,
) -> str:
    payload = json.dumps([origin, dest, via], sort_keys=True)
    return f"osrm:route:{hashlib.sha256(payload.encode()).hexdigest()}"


def _coord_path(points: list[tuple[float, float]]) -> str:
    return ";".join(f"{lon},{lat}" for lat, lon in points)


def _parse_route(route: dict[str, Any]) -> dict | None:
    geometry = route.get("geometry")
    if not geometry or not isinstance(geometry, str):
        return None
    length_m = float(route.get("distance", 0))
    duration_s = float(route.get("duration", 0))
    sections: list[dict[str, float]] = []
    for leg in route.get("legs") or []:
        for step in leg.get("steps") or []:
            sections.append(
                {
                    "length_m": float(step.get("distance", 0)),
                    "duration_s": float(step.get("duration", 0)),
                }
            )
    if not sections:
        sections = [{"length_m": length_m, "duration_s": duration_s}]
    return {
        "polyline": geometry,
        "length_m": length_m,
        "duration_s": duration_s,
        "sections": sections,
    }


def _fetch_routes(
    origin: tuple[float, float],
    dest: tuple[float, float],
    via: tuple[float, float] | None = None,
) -> list[dict]:
    points = [origin, dest] if via is None else [origin, via, dest]
    path = _coord_path(points)
    base = settings.OSRM_BASE_URL.rstrip("/")
    url = f"{base}/route/v1/driving/{path}"
    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "true",
        "alternatives": "true",
    }
    data = _request(url, params)
    routes: list[dict] = []
    for r in data.get("routes") or []:
        parsed = _parse_route(r)
        if parsed:
            routes.append(parsed)
    return routes


def _geometry_key(polyline: str) -> str:
    return hashlib.sha256(polyline.encode()).hexdigest()[:16]


def truck_routes(
    origin: tuple[float, float],
    dest: tuple[float, float],
) -> tuple[list[dict], list[str]]:
    cache_key = _route_key(origin, dest, None)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    warnings: list[str] = []
    routes = _fetch_routes(origin, dest)
    seen: set[str] = set()
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
        try:
            extra = _fetch_routes(origin, dest, via=(mid_lat, mid_lon))
        except ProviderError:
            extra = []
            warnings.append(
                "The additional route could not be retrieved. Available routes are shown."
            )
        for r in extra:
            gk = _geometry_key(r["polyline"])
            if gk in seen:
                continue
            seen.add(gk)
            unique.append(r)

    if len(unique) < 3:
        warnings.append(
            f"OSRM returned {len(unique)} distinct route(s); fewer than 3 alternatives available."
        )

    result = (unique[:3], warnings)
    cache.set(cache_key, result, settings.CACHE_TTL_ROUTE)
    return result
