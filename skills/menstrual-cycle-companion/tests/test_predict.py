import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import db
import predict


class TestPrediction(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.orig_env = os.environ.get("MCC_DATA_DIR")
        os.environ["MCC_DATA_DIR"] = self.temp_dir.name

        def restore_env():
            if self.orig_env is None:
                os.environ.pop("MCC_DATA_DIR", None)
            else:
                os.environ["MCC_DATA_DIR"] = self.orig_env

        self.addCleanup(restore_env)
        db.init_db()

    def test_predict_unknown_profile(self):
        with self.assertRaises(ValueError):
            predict.predict("nonexistent")

    def test_predict_needs_bootstrap(self):
        db.add_profile("alex", "cycler")
        res = predict.predict("alex")
        self.assertEqual(res["status"], "needs_bootstrap")

    def test_predict_bootstrap_with_one_start(self):
        db.add_profile(
            "alex",
            "cycler",
            bootstrap_cycle_length=28,
            bootstrap_period_length=5,
            bootstrap_luteal_length=14,
        )
        db.log_period_start("alex", "2026-08-01")
        res = predict.predict("alex")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["predicted_cycle_length_days"], 28)
        self.assertEqual(res["next_period"]["estimate"], "2026-08-29")
        self.assertEqual(res["estimated_ovulation"], "2026-08-15")
        self.assertEqual(res["fertile_window"]["start"], "2026-08-10")
        self.assertEqual(res["fertile_window"]["end"], "2026-08-16")
        self.assertIn("bootstrap", res["confidence"])

    def test_predict_from_logged_history(self):
        db.add_profile("alex", "cycler", bootstrap_cycle_length=28)
        # 3 cycles: starts at Day 0, Day 28, Day 57 (intervals: 28 days, 29 days)
        base = date(2026, 5, 1)
        d1 = base.isoformat()
        d2 = (base + timedelta(days=28)).isoformat()
        d3 = (base + timedelta(days=57)).isoformat()

        db.log_period_start("alex", d1)
        db.log_period_start("alex", d2)
        db.log_period_start("alex", d3)

        res = predict.predict("alex")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["based_on"], "last 2 logged cycle(s)")
        self.assertIn(res["predicted_cycle_length_days"], [28, 29])
        self.assertEqual(res["last_period_start"], d3)
        self.assertIn("estimate", res["next_period"])
        self.assertIn("estimated_ovulation", res)
        self.assertIn("fertile_window", res)


if __name__ == "__main__":
    unittest.main()
