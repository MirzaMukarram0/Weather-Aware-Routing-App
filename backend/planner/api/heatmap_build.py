"""Build corridor heatmap payload."""

from __future__ import annotations

from datetime import datetime, timedelta

from planner.domain.checkpoints import polylines_to_latlon_lines
from planner.domain.geo import coord_key
from planner.domain.heatmap import build_grid
from planner.domain.risk import UNKNOWN, classify_checkpoint, level_label
from planner.providers.errors import ProviderError
from planner.providers.open_meteo import fetch_series_for_locations, sample_at_eta


def build_heatmap(
    polylines: list[str],
    departure: datetime,
    load_lb: float,
) -> dict:
    route_lines = polylines_to_latlon_lines(polylines)
    if not route_lines:
        raise ValueError("No route geometries")

    cells, cell_mi = build_grid(route_lines)
    timestamps = [departure + timedelta(hours=h) for h in range(49)]
    end_ts = timestamps[-1]
    locs = [coord_key(c.lat, c.lon) for c in cells]

    warnings: list[str] = []
    try:
        series_map = fetch_series_for_locations(locs, departure, end_ts)
    except ProviderError as e:
        series_map = {}
        warnings.append(f"Weather data unavailable for heatmap: {e}")

    cell_payload = []
    for cell in cells:
        ck = coord_key(cell.lat, cell.lon)
        series = series_map.get(ck)
        hours: list[str] = []
        for ts in timestamps:
            if series is None:
                hours.append(UNKNOWN)
                continue
            sample = sample_at_eta(series, ts)
            hours.append(level_label(classify_checkpoint(sample, load_lb).level))
        cell_payload.append(
            {
                "id": cell.id,
                "lat": cell.lat,
                "lon": cell.lon,
                "polygon": [{"lat": a, "lon": b} for a, b in cell.polygon],
                "levels_by_hour": hours,
            }
        )

    if any(UNKNOWN in cell["levels_by_hour"] for cell in cell_payload) and not warnings:
        warnings.append("Some corridor forecasts are unavailable and shown in gray.")

    return {
        "cell_mi": cell_mi,
        "timestamps_utc": [t.isoformat() for t in timestamps],
        "cells": cell_payload,
        "warnings": warnings,
    }
