from django.test import SimpleTestCase

from planner.domain.ranking import CheckpointMiles, attribute_miles, rank_key, recommend_routes
from planner.domain.risk import (
    UNKNOWN,
    Level,
    WeatherSample,
    apply_load_rules_wind,
    classify_checkpoint,
    rain_level_in_hr,
    snow_level_in_hr,
    wind_level_mph,
)


class RiskBoundaryTests(SimpleTestCase):
    def test_wind_edges(self):
        self.assertEqual(wind_level_mph(24.9), Level.LOW)
        self.assertEqual(wind_level_mph(25), Level.MODERATE)
        self.assertEqual(wind_level_mph(54.9), Level.SEVERE)
        self.assertEqual(wind_level_mph(55), Level.NO_TRAVEL)

    def test_rain_edges(self):
        self.assertEqual(rain_level_in_hr(0.099), Level.LOW)
        self.assertEqual(rain_level_in_hr(0.10), Level.MODERATE)
        self.assertEqual(rain_level_in_hr(0.25), Level.HIGH)
        self.assertEqual(rain_level_in_hr(1.0), Level.SEVERE)
        self.assertEqual(rain_level_in_hr(1.0001), Level.NO_TRAVEL)

    def test_snow_edges(self):
        self.assertEqual(snow_level_in_hr(3.0), Level.SEVERE)
        self.assertEqual(snow_level_in_hr(3.0001), Level.NO_TRAVEL)

    def test_load_rules(self):
        self.assertEqual(apply_load_rules_wind(Level.SEVERE, 50, 30_000), Level.SEVERE)
        self.assertEqual(apply_load_rules_wind(Level.SEVERE, 50, 30_001), Level.NO_TRAVEL)
        self.assertEqual(apply_load_rules_wind(Level.HIGH, 40, 40_000), Level.HIGH)
        self.assertEqual(apply_load_rules_wind(Level.HIGH, 40, 40_001), Level.SEVERE)

    def test_gust_dominates(self):
        r = classify_checkpoint(WeatherSample(20, 45, 0, 0), 10_000)
        self.assertEqual(r.level, Level.SEVERE)

    def test_missing_weather_unknown(self):
        r = classify_checkpoint(WeatherSample(None, None, None, None), 10_000)
        self.assertEqual(r.level, UNKNOWN)


class RankingTests(SimpleTestCase):
    def test_miles_sum(self):
        cps = [
            CheckpointMiles(0, Level.LOW),
            CheckpointMiles(25, Level.HIGH),
            CheckpointMiles(50, Level.LOW),
        ]
        s = attribute_miles(cps)
        owned = s.low_mi + s.high_mi + s.moderate_mi + s.severe_mi + s.no_travel_mi + s.unknown_mi
        self.assertAlmostEqual(owned, 50.0)

    def test_tie_break_duration(self):
        s = attribute_miles([CheckpointMiles(0, Level.LOW), CheckpointMiles(10, Level.LOW)])
        k1 = rank_key(s, 100)
        k2 = rank_key(s, 200)
        self.assertLess(k1[-1], k2[-1])

    def test_recommendation_warnings(self):
        bad = attribute_miles([CheckpointMiles(0, Level.NO_TRAVEL), CheckpointMiles(10, Level.LOW)])
        good = attribute_miles([CheckpointMiles(0, Level.LOW), CheckpointMiles(10, Level.LOW)])
        rec = recommend_routes([bad, good], [100, 100])
        self.assertEqual(rec.route_index, 1)
        self.assertFalse(rec.warnings)
