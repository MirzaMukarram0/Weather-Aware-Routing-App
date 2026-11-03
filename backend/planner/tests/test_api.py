from django.test import Client, TestCase, override_settings


class HealthTests(TestCase):
    def test_health(self):
        res = Client().get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")


class LocationApiTests(TestCase):
    def test_locations_requires_query(self):
        res = Client().get("/api/locations")
        self.assertEqual(res.status_code, 400)

    @override_settings(HERE_API_KEY="")
    def test_locations_without_api_key(self):
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
            "departure": "2026-06-01T12:00:00Z",
            "timezone": "America/Chicago",
            "load_lb": 0,
            "interval_mi": 25,
        }
        res = Client().post("/api/plan", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 400)

    @override_settings(HERE_API_KEY="")
    def test_plan_without_here_key(self):
        payload = {
            "origin_lat": 41.88,
            "origin_lon": -87.63,
            "dest_lat": 39.74,
            "dest_lon": -104.99,
            "departure": "2026-06-01T12:00:00Z",
            "timezone": "America/Chicago",
            "load_lb": 25000,
            "interval_mi": 25,
        }
        res = Client().post("/api/plan", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 502)


class HeatmapApiValidationTests(TestCase):
    def test_heatmap_rejects_empty_routes(self):
        payload = {
            "departure": "2026-06-01T12:00:00Z",
            "timezone": "America/Chicago",
            "load_lb": 25000,
            "routes": [],
        }
        res = Client().post("/api/heatmap", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 400)
