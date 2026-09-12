import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest.mock import patch

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_due_notifications
import db
import notify


class TestNotifications(unittest.TestCase):
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

    def test_due_events_skips_partner_profiles(self):
        # Only partner profile exists
        db.add_profile("sam", "partner")
        events = check_due_notifications.due_events()
        self.assertEqual(events, [])

    def test_due_events_generates_period_and_fertile_alerts(self):
        # Create cycler profile and linked partner
        cycler_id = db.add_profile(
            "alex", "cycler", bootstrap_cycle_length=28, bootstrap_luteal_length=14
        )
        db.add_profile("sam", "partner", linked_profile_id=cycler_id)

        # Set last period start so that next period is in 2 days
        today = datetime.now().astimezone().date()
        # Next period estimate is last_start + 28 days
        # We want next period to be today + 2 days -> last_start = today - 26 days
        last_start = today - timedelta(days=26)
        db.log_period_start("alex", last_start.isoformat())

        events = check_due_notifications.due_events()
        self.assertTrue(len(events) >= 1)
        event_types = [e["event_type"] for e in events]
        self.assertIn("period_upcoming", event_types)

        period_event = next(e for e in events if e["event_type"] == "period_upcoming")
        self.assertEqual(period_event["profile_name"], "alex")
        self.assertEqual(period_event["days_until"], 2)
        self.assertEqual(period_event["linked_partners"], ["sam"])

        # Record notification in DB
        db.record_notification(
            period_event["profile_id"],
            period_event["event_type"],
            period_event["cycle_anchor_date"],
        )

        # Subsequent check should deduplicate and exclude already notified event
        events_after = check_due_notifications.due_events()
        self.assertNotIn(period_event, events_after)

    def test_notify_config_and_stdout(self):
        notify.write_default_config_if_missing()
        self.assertTrue(os.path.exists(notify.get_config_path()))

        buf = io.StringIO()
        with redirect_stdout(buf):
            notify.send("alex", "Your period may arrive in 2 days", title="Cycle alert")
        output = buf.getvalue()
        self.assertIn("[notify -> alex]", output)
        self.assertIn("Your period may arrive in 2 days", output)

    def test_notify_shell_method(self):
        config = {
            "profiles": {
                "alex": {
                    "method": "shell",
                    "command": "echo '{title}: {message}'",
                }
            }
        }
        with open(notify.get_config_path(), "w") as f:
            json.dump(config, f)

        with patch("subprocess.run") as mock_run:
            notify.send("alex", "Test alert", title="Alert")
            mock_run.assert_called_once_with(
                "echo 'Alert: Test alert'", shell=True, check=False
            )


if __name__ == "__main__":
    unittest.main()
