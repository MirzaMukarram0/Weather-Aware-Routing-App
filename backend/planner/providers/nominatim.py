"""OpenStreetMap geocoding via Nominatim (free, no API key)."""

from __future__ import annotations

import hashlib
import time
from threading import Lock
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from planner.providers.errors import ProviderError

NOMINATIM_TIMEOUT = 20.0
# ponytail: Nominatim public API allows ~1 req/s; cache heavily for dev UX.
_last_request_at = 0.0
_request_lock = Lock()


def _throttle() -> None:
    global _last_request_at
    min_gap = 1.05
    elapsed = time.monotonic() - _last_request_at
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    _last_request_at = time.monotonic()


def autosuggest(query: str, limit: int = 8) -> list[dict]:
    if not query.strip():
        return []
    key = f"nom:geo:{hashlib.sha256(query.strip().lower().encode()).hexdigest()}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    url = settings.NOMINATIM_BASE_URL.rstrip("/") + "/search"
    params = {
        "q": query.strip(),
        "format": "json",
        "limit": limit,
        "countrycodes": "us",
    }
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

    try:
        with _request_lock, httpx.Client(timeout=NOMINATIM_TIMEOUT, headers=headers) as client:
            _throttle()
            resp = client.get(url, params=params)
            if resp.status_code >= 400:
                raise ProviderError("Place search is temporarily unavailable. Please try again.")
            data: list[dict[str, Any]] = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        raise ProviderError("Nominatim request failed") from e

    items = []
    for row in data:
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        label = row.get("display_name") or query
        place_id = str(row.get("place_id", label))
        items.append({"id": place_id, "label": label, "lat": lat, "lon": lon})

    cache.set(key, items, settings.CACHE_TTL_GEO)
    return items
