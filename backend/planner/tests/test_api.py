from django.test import Client, TestCase


class HealthTests(TestCase):
    def test_health(self):
        res = Client().get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")
