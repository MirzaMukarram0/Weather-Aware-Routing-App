"""Shared coordinate keys for weather lookups."""

from __future__ import annotations


def coord_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 6), round(lon, 6))
