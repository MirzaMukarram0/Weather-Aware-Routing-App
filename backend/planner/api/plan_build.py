"""Build a full trip plan (routes, weather, recommendation)."""

from __future__ import annotations

from datetime import datetime

from planner.domain.checkpoints import place_checkpoints
from planner.domain.ranking import (
    CheckpointMiles,
    attribute_miles,
    explain_rank,
    rank_key,
    recommend_routes,
)
from planner.domain.risk import WeatherSample, classify_checkpoint, level_label
from planner.providers.errors import ProviderError
from planner.providers.open_meteo import batch_samples
from planner.providers.osrm import truck_routes


def build_plan(
    *,
    origin: tuple[float, float],
    dest: tuple[float, float],
    departure: datetime,
    timezone: str,
    load_lb: float,
    interval_mi: int,
) -> dict:
    routes_raw, route_warnings = truck_routes(origin, dest)
    if not routes_raw:
        raise ProviderError("No truck routes returned")

    route_checkpoints_meta = []
    all_coords: list[tuple[float, float, datetime]] = []
    for route in routes_raw:
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

    samples = batch_samples(all_coords)

    response_routes = []
    summaries = []
    durations = []

    for idx, route in enumerate(routes_raw):
        cps = route_checkpoints_meta[idx]
        cp_out = []
        cp_miles: list[CheckpointMiles] = []
        for cp in cps:
            sample = samples.get(
                (cp.lat, cp.lon, cp.eta_utc), WeatherSample(None, None, None, None)
            )
            risk = classify_checkpoint(sample, load_lb)
            cp_miles.append(CheckpointMiles(cp.distance_mi, risk.level, sample.complete))
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
                    "risk_level": level_label(risk.level),
                    "weather_complete": sample.complete,
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
    keys = [rank_key(s, d) for s, d in zip(summaries, durations, strict=True)]
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    for rank, idx in enumerate(order, start=1):
        response_routes[idx]["rank"] = rank
        response_routes[idx]["comparison_reason"] = (
            rec.reason
            if idx == rec.route_index
            else "Recommended route has " + explain_rank(keys[rec.route_index], keys[idx])
        )
    if any(not s.weather_complete for s in summaries):
        route_warnings = [
            *route_warnings,
            "Some forecasts are unavailable. Unknown miles are excluded from average risk; "
            "comparisons are incomplete.",
        ]
    return {
        "departure_utc": departure.isoformat(),
        "timezone": timezone,
        "interval_mi": interval_mi,
        "warnings": route_warnings,
        "routes": response_routes,
        "recommendation": {
            "route_id": response_routes[rec.route_index]["id"],
            "reason": rec.reason,
            "warnings": rec.warnings,
        },
    }
