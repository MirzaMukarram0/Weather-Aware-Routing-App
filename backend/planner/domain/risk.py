"""Weather and load risk classification (pure functions)."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from enum import IntEnum


class Level(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


UNKNOWN = "UNKNOWN"


def wind_level_mph(wind_mph: float) -> Level:
    return Level(bisect_right((25, 35, 45, 55), wind_mph))


def rain_level_in_hr(rain_in_hr: float) -> Level:
    if rain_in_hr > 1.0:
        return Level.NO_TRAVEL
    return Level(bisect_right((0.10, 0.25, 0.50), rain_in_hr))


def snow_level_in_hr(snow_in_hr: float) -> Level:
    if snow_in_hr > 3.0:
        return Level.NO_TRAVEL
    return Level(bisect_right((0.5, 1.0, 2.0), snow_in_hr))


def apply_load_rules_wind(base: Level, wind_mph: float, load_lb: float) -> Level:
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        return Level.NO_TRAVEL
    if 35 <= wind_mph < 45 and load_lb > 40_000:
        return max(base, Level.SEVERE)
    return base


@dataclass(frozen=True)
class WeatherSample:
    wind_sustained_mph: float | None
    wind_gust_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None

    @property
    def complete(self) -> bool:
        return all(
            v is not None
            for v in (self.wind_sustained_mph, self.wind_gust_mph, self.rain_in_hr, self.snow_in_hr)
        )


@dataclass(frozen=True)
class CheckpointRisk:
    level: Level | str
    wind_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None
    wind_level: Level | str | None = None
    rain_level: Level | str | None = None
    snow_level: Level | str | None = None


def classify_checkpoint(sample: WeatherSample, load_lb: float) -> CheckpointRisk:
    if sample.wind_sustained_mph is None and sample.wind_gust_mph is None:
        if sample.rain_in_hr is None and sample.snow_in_hr is None:
            return CheckpointRisk(UNKNOWN, None, None, None)

    wind_parts = [v for v in (sample.wind_sustained_mph, sample.wind_gust_mph) if v is not None]
    wind_mph = max(wind_parts) if wind_parts else None

    rain = sample.rain_in_hr
    snow = sample.snow_in_hr

    w_level: Level | str = UNKNOWN
    r_level: Level | str = UNKNOWN
    s_level: Level | str = UNKNOWN

    if wind_mph is not None:
        w_level = apply_load_rules_wind(wind_level_mph(wind_mph), wind_mph, load_lb)
    if rain is not None:
        r_level = rain_level_in_hr(rain)
    if snow is not None:
        s_level = snow_level_in_hr(snow)

    known = [x for x in (w_level, r_level, s_level) if isinstance(x, Level)]
    if Level.NO_TRAVEL in known:
        overall: Level | str = Level.NO_TRAVEL
    elif not sample.complete:
        overall = UNKNOWN
    else:
        overall = max(known, key=lambda lv: lv.value)

    return CheckpointRisk(
        level=overall,
        wind_mph=wind_mph,
        rain_in_hr=rain,
        snow_in_hr=snow,
        wind_level=w_level,
        rain_level=r_level,
        snow_level=s_level,
    )


def level_value(level: Level | str) -> int | None:
    if isinstance(level, Level):
        return level.value
    return None


def level_label(level: Level | str) -> str:
    return level.name if isinstance(level, Level) else str(level)
