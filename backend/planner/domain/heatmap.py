"""Bounded, non-overlapping weather cells along the union of route corridors."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GridCell:
    id: str
    lat: float
    lon: float
    polygon: list[tuple[float, float]]


def _distance_to_segment(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / length2)) if length2 else 0
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def build_grid(route_coords, cell_mi=10.0, buffer_mi=20.0, max_cells=500):
    points = [p for line in route_coords for p in line]
    if not points or cell_mi <= 0 or max_cells < 1:
        raise ValueError("Valid route geometries and grid limits are required")
    # Local projection for an approximate forecast grid, not for navigation.
    lat0 = (min(p[0] for p in points) + max(p[0] for p in points)) / 2
    lon0 = (min(p[1] for p in points) + max(p[1] for p in points)) / 2
    lon_scale = 69.0 * max(math.cos(math.radians(lat0)), 0.2)
    lines = [
        [((lon - lon0) * lon_scale, (lat - lat0) * 69) for lat, lon in line]
        for line in route_coords
    ]

    def geographic(x, y):
        return lat0 + y / 69, lon0 + x / lon_scale

    def indices(step):
        found = set()
        radius = math.ceil(buffer_mi / step) + 1
        for line in lines:
            for a, b in zip(line, line[1:]):
                count = max(1, math.ceil(math.dist(a, b) / step))
                for n in range(count + 1):
                    x = a[0] + (b[0] - a[0]) * n / count
                    y = a[1] + (b[1] - a[1]) * n / count
                    ix, iy = math.floor(x / step), math.floor(y / step)
                    for col in range(ix - radius, ix + radius + 1):
                        for row in range(iy - radius, iy + radius + 1):
                            center = ((col + 0.5) * step, (row + 0.5) * step)
                            if _distance_to_segment(*center, a, b) <= buffer_mi + step / 2:
                                found.add((col, row))
                                if len(found) > max_cells:
                                    return found
        return found

    found = indices(cell_mi)
    while len(found) > max_cells:
        cell_mi *= 1.5
        found = indices(cell_mi)
    cells = []
    for i, (col, row) in enumerate(sorted(found)):
        lat, lon = geographic((col + 0.5) * cell_mi, (row + 0.5) * cell_mi)
        polygon = [
            geographic(x * cell_mi, y * cell_mi)
            for x, y in ((col, row), (col + 1, row), (col + 1, row + 1), (col, row + 1))
        ]
        cells.append(GridCell(f"c{i}", lat, lon, polygon))
    return cells, cell_mi
