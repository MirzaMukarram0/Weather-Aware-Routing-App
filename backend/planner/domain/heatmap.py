"""Corridor heatmap grid generation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from planner.domain.risk import Level, WeatherSample, classify_checkpoint


@dataclass(frozen=True)
class GridCell:
    id: str
    lat: float
    lon: float
    polygon: list[tuple[float, float]]


def _cell_half_deg(mi: float, lat: float) -> tuple[float, float]:
    lat_deg = mi / 69.0
    lon_deg = mi / (69.0 * max(math.cos(math.radians(lat)), 0.2))
    return lat_deg / 2, lon_deg / 2


def corridor_bbox(
    route_coords: list[list[tuple[float, float]]], buffer_mi: float
) -> tuple[float, float, float, float]:
    lats = [c[0] for line in route_coords for c in line]
    lons = [c[1] for line in route_coords for c in line]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    dlat = buffer_mi / 69.0
    dlon = buffer_mi / (69.0 * max(math.cos(math.radians((min_lat + max_lat) / 2)), 0.2))
    return min_lat - dlat, min_lon - dlon, max_lat + dlat, max_lon + dlon


def build_grid(
    route_coords: list[list[tuple[float, float]]],
    cell_mi: float = 10.0,
    buffer_mi: float = 20.0,
    max_cells: int = 500,
) -> tuple[list[GridCell], float]:
    min_lat, min_lon, max_lat, max_lon = corridor_bbox(route_coords, buffer_mi)
    cell_mi_eff = cell_mi
    cells: list[GridCell] = []

    while True:
        lat_step = cell_mi_eff / 69.0
        mid_lat = (min_lat + max_lat) / 2
        lon_step = cell_mi_eff / (69.0 * max(math.cos(math.radians(mid_lat)), 0.2))
        cells = []
        lat = min_lat
        idx = 0
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                half_lat, half_lon = _cell_half_deg(cell_mi_eff, lat)
                poly = [
                    (lat - half_lat, lon - half_lon),
                    (lat - half_lat, lon + half_lon),
                    (lat + half_lat, lon + half_lon),
                    (lat + half_lat, lon - half_lon),
                ]
                cells.append(GridCell(id=f"c{idx}", lat=lat, lon=lon, polygon=poly))
                idx += 1
                lon += lon_step
            lat += lat_step
        if len(cells) <= max_cells or cell_mi_eff >= 40:
            return cells, cell_mi_eff
        cell_mi_eff *= 1.5


def risk_for_sample(sample: WeatherSample, load_lb: float) -> Level | str:
    return classify_checkpoint(sample, load_lb).level
