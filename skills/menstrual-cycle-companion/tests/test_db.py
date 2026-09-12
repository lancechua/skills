import os
import sqlite3
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import db


class TestDatabaseLayer(unittest.TestCase):
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

    def test_get_conn_raises_when_uninitialized(self):
        with self.assertRaises(RuntimeError) as ctx, db.get_conn():
            pass
        self.assertIn("Database not found", str(ctx.exception))
        self.assertIn("python cli.py init", str(ctx.exception))

    def test_init_db_creates_tables(self):
        db.init_db()
        self.assertTrue(os.path.exists(db.get_db_path()))
        with db.get_conn() as conn:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            self.assertIn("profiles", tables)
            self.assertIn("period_starts", tables)
            self.assertIn("daily_logs", tables)
            self.assertIn("notification_log", tables)

    def test_add_and_get_profile(self):
        db.init_db()
        pid = db.add_profile(
            "alex",
            "cycler",
            bootstrap_cycle_length=28,
            bootstrap_period_length=5,
            bootstrap_luteal_length=14,
        )
        self.assertEqual(pid, 1)

        profile = db.get_profile("alex")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "alex")
        self.assertEqual(profile["role"], "cycler")
        self.assertEqual(profile["bootstrap_cycle_length"], 28)
        self.assertEqual(profile["bootstrap_period_length"], 5)
        self.assertEqual(profile["bootstrap_luteal_length"], 14)

    def test_role_check_constraint(self):
        db.init_db()
        with self.assertRaises(sqlite3.IntegrityError):
            db.add_profile("invalid_user", "invalid_role")

    def test_link_partner_profile(self):
        db.init_db()
        cycler_id = db.add_profile("alex", "cycler")
        db.add_profile("sam", "partner", linked_profile_id=cycler_id)
        sam = db.get_profile("sam")
        self.assertEqual(sam["linked_profile_id"], cycler_id)

        profiles = db.list_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertEqual([p["name"] for p in profiles], ["alex", "sam"])

    def test_update_bootstrap(self):
        db.init_db()
        db.add_profile("alex", "cycler")
        db.update_bootstrap("alex", cycle_length=30, period_length=6)
        alex = db.get_profile("alex")
        self.assertEqual(alex["bootstrap_cycle_length"], 30)
        self.assertEqual(alex["bootstrap_period_length"], 6)

        with self.assertRaises(ValueError):
            db.update_bootstrap("unknown", cycle_length=28)

    def test_period_starts_insert_and_conflict_update(self):
        db.init_db()
        db.add_profile("alex", "cycler")
        db.log_period_start("alex", "2026-08-01", notes="Original notes")
        db.log_period_start("alex", "2026-08-01", notes="Updated notes")

        starts = db.get_period_starts("alex")
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0]["start_date"], "2026-08-01")
        self.assertEqual(starts[0]["notes"], "Updated notes")

        db.log_period_start("alex", "2026-08-29", notes="Next cycle")
        starts = db.get_period_starts("alex")
        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0]["start_date"], "2026-08-01")
        self.assertEqual(starts[1]["start_date"], "2026-08-29")

    def test_daily_logs_insert_and_merge(self):
        db.init_db()
        db.add_profile("alex", "cycler")
        db.log_daily("alex", "2026-08-15", flow="light", pain=3)
        db.log_daily("alex", "2026-08-15", symptoms="cramps,headache", mood="tired")

        logs = db.get_daily_logs("alex")
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log["flow"], "light")
        self.assertEqual(log["pain"], 3)
        self.assertEqual(log["symptoms"], "cramps,headache")
        self.assertEqual(log["mood"], "tired")

    def test_notifications_recording_and_idempotency(self):
        db.init_db()
        pid = db.add_profile("alex", "cycler")
        self.assertFalse(db.was_notified(pid, "period_upcoming", "2026-09-01"))

        db.record_notification(pid, "period_upcoming", "2026-09-01")
        self.assertTrue(db.was_notified(pid, "period_upcoming", "2026-09-01"))

        # Recording again should not fail or duplicate
        db.record_notification(pid, "period_upcoming", "2026-09-01")
        self.assertTrue(db.was_notified(pid, "period_upcoming", "2026-09-01"))


if __name__ == "__main__":
    unittest.main()
