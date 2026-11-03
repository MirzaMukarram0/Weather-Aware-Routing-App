from __future__ import annotations

from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from planner.api.serializers import (
    HeatmapRequestSerializer,
    LocationQuerySerializer,
    PlanRequestSerializer,
)
from planner.domain.checkpoints import place_checkpoints
from planner.domain.heatmap import build_grid, risk_for_sample
from planner.domain.ranking import CheckpointMiles, attribute_miles, recommend_routes
from planner.domain.risk import UNKNOWN, Level, WeatherSample, classify_checkpoint
from planner.providers.here import ProviderError, autosuggest, truck_routes
from planner.providers.open_meteo import batch_samples, sample_at_eta
from planner.providers.open_meteo_batch import batch_series_for_locations


def _level_name(level: Level | str) -> str:
    if isinstance(level, Level):
        return level.name
    return str(level)


def _error(message: str, code: int = 502) -> Response:
    return Response({"error": message}, status=code)


@api_view(["GET"])
def health(_request: Request) -> Response:
    return Response({"status": "ok"})


@api_view(["GET"])
def locations(request: Request) -> Response:
    ser = LocationQuerySerializer(data=request.query_params)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        items = autosuggest(ser.validated_data["q"])
    except ProviderError as e:
        return _error(str(e), e.status)
    return Response({"items": items})


@api_view(["POST"])
def plan(request: Request) -> Response:
    ser = PlanRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    origin = (data["origin_lat"], data["origin_lon"])
    dest = (data["dest_lat"], data["dest_lon"])
    departure = data["departure"]
    load_lb = data["load_lb"]
    interval_mi = int(data["interval_mi"])

    try:
        routes_raw, route_warnings = truck_routes(origin, dest, load_lb)
    except ProviderError as e:
        return _error(str(e), e.status)

    if not routes_raw:
        return _error("No truck routes returned", 502)

    response_routes = []
    summaries = []
    durations = []

    all_coords: list[tuple[float, float, object]] = []
    route_checkpoints_meta: list[list] = []

    for idx, route in enumerate(routes_raw):
        cps = place_checkpoints(
            route["polyline"],
            route["sections"],
            departure,
            interval_mi,
            route["length_m"],
        )
        route_checkpoints_meta.append(cps)
        for cp in cps:
            all_coords.append((cp.lat, cp.lon, cp.eta_utc))

    try:
        samples = batch_samples(all_coords)
    except ProviderError as e:
        return _error(str(e), e.status)

    for idx, route in enumerate(routes_raw):
        cps = route_checkpoints_meta[idx]
        cp_out = []
        cp_miles: list[CheckpointMiles] = []
        for cp in cps:
            sample = samples.get((cp.lat, cp.lon))
            if sample is None:
                sample = WeatherSample(None, None, None, None)
            risk = classify_checkpoint(sample, load_lb)
            cp_miles.append(CheckpointMiles(cp.distance_mi, risk.level))
            cp_out.append(
                {
                    "lat": cp.lat,
                    "lon": cp.lon,
                    "distance_mi": round(cp.distance_mi, 2),
                    "eta_utc": cp.eta_utc.isoformat(),
                    "weather": {
                        "wind_sustained_mph": sample.wind_sustained_mph,
                        "wind_gust_mph": sample.wind_gust_mph,
                        "rain_in_hr": sample.rain_in_hr,
                        "snow_in_hr": sample.snow_in_hr,
                    },
                    "risk_level": _level_name(risk.level),
                }
            )

        summary = attribute_miles(cp_miles)
        summaries.append(summary)
        durations.append(route["duration_s"])

        response_routes.append(
            {
                "id": f"route-{idx}",
                "distance_mi": round(route["length_m"] / 1609.344, 2),
                "duration_s": int(route["duration_s"]),
                "polyline": route["polyline"],
                "checkpoints": cp_out,
                "summary": {
                    "no_travel_mi": round(summary.no_travel_mi, 2),
                    "severe_mi": round(summary.severe_mi, 2),
                    "high_mi": round(summary.high_mi, 2),
                    "moderate_mi": round(summary.moderate_mi, 2),
                    "low_mi": round(summary.low_mi, 2),
                    "unknown_mi": round(summary.unknown_mi, 2),
                    "avg_risk": summary.avg_risk,
                    "weather_complete": summary.weather_complete,
                },
            }
        )

    rec = recommend_routes(summaries, durations)
    recommended_id = response_routes[rec.route_index]["id"]

    return Response(
        {
            "departure_utc": departure.isoformat(),
            "timezone": data["timezone"],
            "interval_mi": interval_mi,
            "warnings": route_warnings,
            "routes": response_routes,
            "recommendation": {
                "route_id": recommended_id,
                "reason": rec.reason,
                "warnings": rec.warnings,
            },
        }
    )


@api_view(["POST"])
def heatmap(request: Request) -> Response:
    ser = HeatmapRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    departure = data["departure"]
    load_lb = data["load_lb"]
    route_lines: list[list[tuple[float, float]]] = []
    import polyline as polyline_lib

    for r in data["routes"]:
        enc = r.get("polyline")
        if not enc:
            continue
        pts = polyline_lib.decode(enc, precision=5)
        route_lines.append([(p[0], p[1]) for p in pts])

    if not route_lines:
        return Response({"error": "No route geometries"}, status=400)

    cells, cell_mi = build_grid(route_lines)
    timestamps = [departure + timedelta(hours=h) for h in range(49)]

    cell_payload = []
    end_ts = timestamps[-1]
    locs = [(c.lat, c.lon) for c in cells]
    try:
        series_map = batch_series_for_locations(locs, departure, end_ts)
    except ProviderError:
        series_map = {}
    for cell in cells:
        series = series_map.get((cell.lat, cell.lon))
        hours: list[str] = []
        for ts in timestamps:
            if series is None:
                hours.append(UNKNOWN)
                continue
            sample = sample_at_eta(series, ts)
            level = risk_for_sample(sample, load_lb)
            hours.append(_level_name(level))
        cell_payload.append(
            {
                "id": cell.id,
                "lat": cell.lat,
                "lon": cell.lon,
                "polygon": [{"lat": a, "lon": b} for a, b in cell.polygon],
                "levels_by_hour": hours,
            }
        )

    return Response(
        {
            "cell_mi": cell_mi,
            "timestamps_utc": [t.isoformat() for t in timestamps],
            "cells": cell_payload,
        }
    )
