"""Route summarization and recommendation ranking."""

from __future__ import annotations

from dataclasses import dataclass

from planner.domain.risk import UNKNOWN, Level


@dataclass(frozen=True)
class CheckpointMiles:
    distance_mi: float
    level: Level | str
    weather_complete: bool = True


@dataclass(frozen=True)
class RouteSummary:
    no_travel_mi: float
    severe_mi: float
    high_mi: float
    moderate_mi: float
    low_mi: float
    unknown_mi: float
    avg_risk: float | None
    weather_complete: bool


RANK_FIELDS = ("no_travel_mi", "severe_mi", "high_mi", "avg_risk", "duration_s")
RANK_LABELS = {
    "no_travel_mi": "fewest no-travel miles",
    "severe_mi": "fewest severe miles",
    "high_mi": "fewest high miles",
    "avg_risk": "lowest average risk",
    "duration_s": "shortest travel time",
}


def attribute_miles(checkpoints: list[CheckpointMiles]) -> RouteSummary:
    if not checkpoints:
        return RouteSummary(0, 0, 0, 0, 0, 0, None, True)

    n = len(checkpoints)
    totals = {
        Level.LOW: 0.0,
        Level.MODERATE: 0.0,
        Level.HIGH: 0.0,
        Level.SEVERE: 0.0,
        Level.NO_TRAVEL: 0.0,
    }
    unknown_mi = 0.0
    weighted = 0.0
    known_mi = 0.0
    incomplete = False

    for i, cp in enumerate(checkpoints):
        incomplete = incomplete or not cp.weather_complete
        if i == 0:
            owned = checkpoints[1].distance_mi - cp.distance_mi if n > 1 else 0.0
            owned /= 2
        elif i == n - 1:
            owned = (cp.distance_mi - checkpoints[i - 1].distance_mi) / 2
        else:
            owned = (checkpoints[i + 1].distance_mi - checkpoints[i - 1].distance_mi) / 2

        owned = max(0.0, owned)
        lv = cp.level
        if lv == UNKNOWN or not isinstance(lv, Level):
            unknown_mi += owned
            incomplete = True
            continue
        totals[lv] += owned
        weighted += lv.value * owned
        known_mi += owned

    avg = weighted / known_mi if known_mi > 0 else None
    return RouteSummary(
        no_travel_mi=totals[Level.NO_TRAVEL],
        severe_mi=totals[Level.SEVERE],
        high_mi=totals[Level.HIGH],
        moderate_mi=totals[Level.MODERATE],
        low_mi=totals[Level.LOW],
        unknown_mi=unknown_mi,
        avg_risk=avg,
        weather_complete=not incomplete and unknown_mi == 0,
    )


def rank_key(summary: RouteSummary, duration_s: float) -> tuple:
    avg = summary.avg_risk if summary.avg_risk is not None else float("inf")
    return (summary.no_travel_mi, summary.severe_mi, summary.high_mi, avg, duration_s)


def explain_rank(winner_key: tuple, loser_key: tuple) -> str:
    for field, w_val, l_val in zip(RANK_FIELDS, winner_key, loser_key, strict=True):
        if w_val != l_val:
            return RANK_LABELS[field]
    return "all criteria tied"


@dataclass(frozen=True)
class Recommendation:
    route_index: int
    reason: str
    warnings: list[str]


def recommend_routes(summaries: list[RouteSummary], durations_s: list[float]) -> Recommendation:
    keys = [rank_key(s, d) for s, d in zip(summaries, durations_s, strict=True)]
    winner = min(range(len(keys)), key=lambda i: keys[i])
    warnings: list[str] = []
    s = summaries[winner]
    if s.no_travel_mi > 0:
        warnings.append("Recommended route includes no-travel segments.")
    if not s.weather_complete:
        warnings.append("Recommended route has incomplete weather coverage.")
    reason = "Best overall by ranking"
    if len(keys) > 1:
        others = sorted((i for i in range(len(keys)) if i != winner), key=lambda i: keys[i])
        if others:
            reason = explain_rank(keys[winner], keys[others[0]])
    return Recommendation(route_index=winner, reason=reason, warnings=warnings)
