from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from planner.domain.heatmap import build_grid
from planner.domain.ranking import CheckpointMiles, attribute_miles, recommend_routes
from planner.domain.risk import UNKNOWN, Level, WeatherSample, classify_checkpoint
from planner.providers.open_meteo import batch_samples, sample_at_eta


def series():
    return {
        "hourly": {
            "time": ["2026-11-03T17:00", "2026-11-03T18:00"],
            "wind_speed_10m": [10, 50],
            "wind_gusts_10m": [15, 54.9],
            "rain": [0, 0.1],
            "showers": [0, 0.15],
            "snowfall": [0, 0],
        }
    }


class CorrectnessRegressionTests(SimpleTestCase):
    def test_decimal_load_boundaries(self):
        for wind, load, expected in [
            (44.9, 40001, Level.SEVERE),
            (54.9, 30001, Level.NO_TRAVEL),
            (24.9999, 25000, Level.LOW),
            (34.9999, 25000, Level.MODERATE),
        ]:
            with self.subTest(wind=wind):
                self.assertEqual(
                    classify_checkpoint(WeatherSample(wind, wind, 0, 0), load).level, expected
                )

    def test_partial_weather_is_unknown_unless_no_travel_known(self):
        for sample in [
            WeatherSample(10, None, 0, 0),
            WeatherSample(10, 12, None, 0),
            WeatherSample(10, 12, 0, None),
        ]:
            self.assertEqual(classify_checkpoint(sample, 25000).level, UNKNOWN)
        self.assertEqual(
            classify_checkpoint(WeatherSample(60, None, None, None), 25000).level, Level.NO_TRAVEL
        )

    def test_no_travel_does_not_conceal_incomplete_coverage(self):
        summary = attribute_miles(
            [CheckpointMiles(0, Level.NO_TRAVEL, False), CheckpointMiles(10, Level.LOW)]
        )
        self.assertFalse(summary.weather_complete)
        self.assertEqual(summary.no_travel_mi, 5)

    def test_forecast_rounding_and_no_stale_substitution(self):
        eta = datetime(2026, 11, 3, 17, 30, tzinfo=UTC)
        sample = sample_at_eta(series(), eta)
        self.assertEqual(sample.wind_gust_mph, 54.9)
        self.assertEqual(sample.rain_in_hr, 0.25)
        for hour in [16, 19]:
            sample = sample_at_eta(series(), eta.replace(hour=hour, minute=0))
            self.assertIsNone(sample.wind_gust_mph)
            self.assertIsNone(sample.rain_in_hr)

    def test_missing_showers_not_zero(self):
        data = series()
        data["hourly"]["showers"][1] = None
        sample = sample_at_eta(data, datetime(2026, 11, 3, 18, tzinfo=UTC))
        self.assertIsNone(sample.rain_in_hr)

    @patch("planner.providers.open_meteo.fetch_series_for_locations")
    def test_same_coordinate_different_arrival_keeps_both_forecasts(self, fetch):
        fetch.return_value = {(40.0, -90.0): series()}
        a = (40.0, -90.0, datetime(2026, 11, 3, 17, tzinfo=UTC))
        b = (40.0, -90.0, a[2] + timedelta(hours=1))
        samples = batch_samples([a, b])
        self.assertEqual(samples[a].wind_gust_mph, 15)
        self.assertEqual(samples[b].wind_gust_mph, 54.9)

    def test_grid_follows_corridor_not_bounding_rectangle(self):
        cells, _ = build_grid([[(35, -100), (40, -90)]])
        self.assertTrue(cells)
        self.assertLessEqual(len(cells), 500)
        self.assertFalse(any(c.lat > 39 and c.lon < -98 for c in cells))

    def test_long_trip_grid_always_capped(self):
        cells, resolution = build_grid([[(25, -125), (48, -68)]], max_cells=30)
        self.assertLessEqual(len(cells), 30)
        self.assertGreater(resolution, 10)

    def test_warning_when_every_route_is_unknown(self):
        s = attribute_miles([CheckpointMiles(0, UNKNOWN), CheckpointMiles(10, UNKNOWN)])
        rec = recommend_routes([s, s], [200, 100])
        self.assertEqual(rec.route_index, 1)
        self.assertTrue(rec.warnings)

    def test_each_ranking_tiebreak(self):
        from planner.domain.ranking import RouteSummary

        for field in ["no_travel_mi", "severe_mi", "high_mi", "avg_risk"]:
            common = dict(
                no_travel_mi=0,
                severe_mi=0,
                high_mi=0,
                moderate_mi=0,
                low_mi=10,
                unknown_mi=0,
                avg_risk=0,
                weather_complete=True,
            )
            worse = {**common, field: 1}
            with self.subTest(field=field):
                rec = recommend_routes([RouteSummary(**worse), RouteSummary(**common)], [100, 200])
                self.assertEqual(rec.route_index, 1)


class WeatherCacheTests(SimpleTestCase):
    def test_cached_series_avoids_http(self):
        from planner.providers.open_meteo import _cache_key, fetch_series_for_locations

        start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)
        key = _cache_key(
            40, -90, start.strftime("%Y-%m-%d"), (end + timedelta(hours=1)).strftime("%Y-%m-%d")
        )
        cache.set(key, series())
        try:
            with patch("planner.providers.open_meteo.httpx.Client") as client:
                result = fetch_series_for_locations([(40, -90)], start, end)
                self.assertIn((40, -90), result)
                client.assert_not_called()
        finally:
            cache.delete(key)
