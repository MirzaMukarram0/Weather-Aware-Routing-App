from datetime import UTC, datetime

from django.test import SimpleTestCase

from planner.domain.checkpoints import place_checkpoints


class CheckpointTests(SimpleTestCase):
    def test_monotonic_eta(self):
        # Simple straight-ish route encoded as short polyline near NYC
        import polyline as polyline_lib

        pts = [(40.0, -75.0), (40.5, -75.5), (41.0, -76.0)]
        enc = polyline_lib.encode(pts, precision=5)
        sections = [
            {"length_m": 80000, "duration_s": 3600},
            {"length_m": 80000, "duration_s": 3600},
        ]
        dep = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        cps = place_checkpoints(enc, sections, dep, 25, 160000)
        self.assertGreaterEqual(len(cps), 2)
        for a, b in zip(cps, cps[1:], strict=False):
            self.assertLessEqual(a.eta_utc, b.eta_utc)
