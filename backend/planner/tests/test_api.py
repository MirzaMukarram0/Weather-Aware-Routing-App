from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from planner.providers.errors import ProviderError


class HealthTests(TestCase):
    def test_health(self):
        res = Client().get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")


class LocationApiTests(TestCase):
    def test_locations_requires_query(self):
        res = Client().get("/api/locations")
        self.assertEqual(res.status_code, 400)

    @patch("planner.api.views.autosuggest", side_effect=ProviderError("Geocoder unavailable"))
    def test_locations_provider_error(self, _mock):
        res = Client().get("/api/locations", {"q": "Chicago"})
        self.assertEqual(res.status_code, 502)
        self.assertIn("error", res.json())


class PlanApiValidationTests(TestCase):
    def test_plan_rejects_empty_body(self):
        res = Client().post("/api/plan", data={}, content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_plan_rejects_invalid_load(self):
        payload = {
            "origin_lat": 41.88,
            "origin_lon": -87.63,
            "dest_lat": 39.74,
            "dest_lon": -104.99,
            "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
            "timezone": "America/Chicago",
            "load_lb": 0,
            "interval_mi": 25,
        }
        res = Client().post("/api/plan", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 400)

    @patch(
        "planner.api.plan_build.truck_routes",
        side_effect=ProviderError("Routing unavailable"),
    )
    def test_plan_routing_provider_error(self, _mock):
        payload = {
            "origin_lat": 41.88,
            "origin_lon": -87.63,
            "dest_lat": 39.74,
            "dest_lon": -104.99,
            "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
            "timezone": "America/Chicago",
            "load_lb": 25000,
            "interval_mi": 25,
        }
        res = Client().post("/api/plan", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 502)


class HeatmapApiValidationTests(TestCase):
    def test_heatmap_rejects_empty_routes(self):
        payload = {
            "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
            "timezone": "America/Chicago",
            "load_lb": 25000,
            "routes": [],
        }
        res = Client().post("/api/heatmap", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 400)
