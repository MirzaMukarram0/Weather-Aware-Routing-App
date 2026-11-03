"""Checkpoint placement and ETA interpolation along route polylines."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import polyline as polyline_lib


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteSpan:
    start_m: float
    end_m: float
    duration_s: float


@dataclass(frozen=True)
class Checkpoint:
    lat: float
    lon: float
    distance_mi: float
    eta_utc: datetime


def haversine_m(a: LatLon, b: LatLon) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dl = math.radians(b.lon - a.lon)
    x = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def decode_flex_polyline(encoded: str) -> list[LatLon]:
    pts = polyline_lib.decode(encoded, precision=5)
    return [LatLon(lat=p[0], lon=p[1]) for p in pts]


def cumulative_distances_m(points: list[LatLon]) -> list[float]:
    if not points:
        return []
    dists = [0.0]
    for i in range(1, len(points)):
        dists.append(dists[-1] + haversine_m(points[i - 1], points[i]))
    return dists


def scale_cumulative(dists_m: list[float], target_m: float) -> list[float]:
    if not dists_m:
        return dists_m
    total = dists_m[-1]
    if total <= 0:
        return dists_m
    factor = target_m / total
    return [d * factor for d in dists_m]


def interpolate_point(points: list[LatLon], dists_m: list[float], at_m: float) -> LatLon:
    if at_m <= 0:
        return points[0]
    if at_m >= dists_m[-1]:
        return points[-1]
    for i in range(1, len(dists_m)):
        if dists_m[i] >= at_m:
            seg_len = dists_m[i] - dists_m[i - 1]
            if seg_len <= 0:
                return points[i]
            t = (at_m - dists_m[i - 1]) / seg_len
            a, b = points[i - 1], points[i]
            return LatLon(lat=a.lat + t * (b.lat - a.lat), lon=a.lon + t * (b.lon - a.lon))
    return points[-1]


def duration_at_distance_m(spans: list[RouteSpan], at_m: float) -> float:
    if not spans or at_m <= 0:
        return 0.0
    total = 0.0
    for span in spans:
        if at_m <= span.start_m:
            break
        if at_m >= span.end_m:
            total += span.duration_s
            continue
        seg = span.end_m - span.start_m
        if seg <= 0:
            total += span.duration_s
        else:
            total += span.duration_s * ((at_m - span.start_m) / seg)
        break
    return total


def build_spans_from_sections(sections: list[dict]) -> tuple[list[RouteSpan], float]:
    spans: list[RouteSpan] = []
    cursor = 0.0
    total_s = 0.0
    for sec in sections:
        length_m = float(sec.get("length_m", 0))
        dur = float(sec.get("duration_s", 0))
        spans.append(RouteSpan(start_m=cursor, end_m=cursor + length_m, duration_s=dur))
        cursor += length_m
        total_s += dur
    return spans, total_s


def place_checkpoints(
    encoded_polyline: str,
    sections: list[dict],
    departure_utc: datetime,
    interval_mi: float,
    reported_length_m: float,
) -> list[Checkpoint]:
    points = decode_flex_polyline(encoded_polyline)
    if len(points) < 2:
        return []

    dists = cumulative_distances_m(points)
    dists = scale_cumulative(dists, reported_length_m)
    spans, _ = build_spans_from_sections(sections)

    interval_m = interval_mi * 1609.344
    total_m = dists[-1]
    targets_m = {0.0, total_m}
    d = interval_m
    while d < total_m - 1e-3:
        targets_m.add(d)
        d += interval_m

    checkpoints: list[Checkpoint] = []
    for at_m in sorted(targets_m):
        pt = interpolate_point(points, dists, at_m)
        dur_s = duration_at_distance_m(spans, at_m)
        checkpoints.append(
            Checkpoint(
                lat=pt.lat,
                lon=pt.lon,
                distance_mi=at_m / 1609.344,
                eta_utc=departure_utc + timedelta(seconds=dur_s),
            )
        )
    return checkpoints
