"""Weather and load risk classification (pure functions)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum


class Level(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Band:
    upper_inclusive: float
    level: Level


# Lower-inclusive bands: first band where value <= upper_inclusive wins for finite uppers.
# NO_TRAVEL uses upper_inclusive=inf sentinel via separate check.

WIND_BANDS: tuple[Band, ...] = (
    Band(24.999, Level.LOW),
    Band(34.999, Level.MODERATE),
    Band(44.999, Level.HIGH),
    Band(54.999, Level.SEVERE),
)

RAIN_BANDS: tuple[Band, ...] = (
    Band(0.099999, Level.LOW),
    Band(0.249999, Level.MODERATE),
    Band(0.499999, Level.HIGH),
    Band(1.0, Level.SEVERE),
)

SNOW_BANDS: tuple[Band, ...] = (
    Band(0.499999, Level.LOW),
    Band(0.999999, Level.MODERATE),
    Band(1.999999, Level.HIGH),
    Band(3.0, Level.SEVERE),
)


def level_for(value: float, bands: Sequence[Band], no_travel_above: float) -> Level:
    if value >= no_travel_above:
        return Level.NO_TRAVEL
    for band in bands:
        if value <= band.upper_inclusive:
            return band.level
    return Level.NO_TRAVEL


def wind_level_mph(wind_mph: float) -> Level:
    if wind_mph >= 55:
        return Level.NO_TRAVEL
    return level_for(wind_mph, WIND_BANDS, no_travel_above=55)


def rain_level_in_hr(rain_in_hr: float) -> Level:
    if rain_in_hr > 1.0:
        return Level.NO_TRAVEL
    return level_for(rain_in_hr, RAIN_BANDS, no_travel_above=1.0001)


def snow_level_in_hr(snow_in_hr: float) -> Level:
    if snow_in_hr > 3.0:
        return Level.NO_TRAVEL
    return level_for(snow_in_hr, SNOW_BANDS, no_travel_above=3.0001)


def apply_load_rules_wind(base: Level, wind_mph: float, load_lb: float) -> Level:
    if 45 <= wind_mph <= 54 and load_lb > 30_000:
        return Level.NO_TRAVEL
    if 35 <= wind_mph <= 44 and load_lb > 40_000:
        return max(base, Level.SEVERE)
    return base


@dataclass(frozen=True)
class WeatherSample:
    wind_sustained_mph: float | None
    wind_gust_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None


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
    if not known:
        overall: Level | str = UNKNOWN
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
