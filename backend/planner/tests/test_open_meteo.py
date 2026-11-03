from datetime import UTC, datetime

from django.test import SimpleTestCase

from planner.providers.open_meteo import sample_at_eta


class OpenMeteoTimeTests(SimpleTestCase):
    def test_sample_at_eta_naive_hourly_times(self):
        """Open-Meteo returns naive ISO hours when timezone=UTC; ETAs are aware."""
        series = {
            "hourly": {
                "time": ["2026-11-03T17:00", "2026-11-03T18:00"],
                "wind_speed_10m": [10.0, 20.0],
                "wind_gusts_10m": [15.0, 25.0],
                "rain": [0.0, 0.1],
                "showers": [0.0, 0.0],
                "snowfall": [0.0, 0.0],
            }
        }
        eta = datetime(2026, 11, 3, 17, 45, tzinfo=UTC)
        sample = sample_at_eta(series, eta)
        self.assertEqual(sample.wind_sustained_mph, 20.0)
