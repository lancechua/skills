import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import cli
import db


class TestCLI(unittest.TestCase):
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

    def run_cli(self, args):
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with (
            patch_argv(["cli.py"] + args),
            redirect_stdout(stdout_buf),
            redirect_stderr(stderr_buf),
        ):
            try:
                cli.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code
        return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_cli_requires_init_first(self):
        code, _out, err = self.run_cli(["add-profile", "alex", "cycler"])
        self.assertEqual(code, 1)
        self.assertIn("Database not found", err)
        self.assertIn("python cli.py init", err)

    def test_cli_end_to_end_flow(self):
        # 1. init
        code, _out, _err = self.run_cli(["init"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(db.get_db_path()))

        # 2. add-profile
        code, out, _err = self.run_cli(
            [
                "add-profile",
                "alex",
                "cycler",
                "--cycle-length",
                "28",
                "--period-length",
                "5",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Added profile 'alex'", out)

        # 3. add partner profile
        code, _out, _err = self.run_cli(["add-profile", "sam", "partner"])
        self.assertEqual(code, 0)

        # 4. link partner
        code, out, _err = self.run_cli(["link", "sam", "alex"])
        self.assertEqual(code, 0)
        self.assertIn("Linked sam as supporting partner of alex", out)

        # 5. update bootstrap
        code, out, _err = self.run_cli(
            ["bootstrap", "alex", "--cycle-length", "29"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Updated bootstrap values for 'alex'", out)

        # 6. log-period
        code, out, _err = self.run_cli(
            [
                "log-period",
                "alex",
                "--date",
                "2026-08-01",
                "--notes",
                "Started early morning",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Logged period start for alex on 2026-08-01", out)

        # 7. log-daily
        code, out, _err = self.run_cli(
            [
                "log-daily",
                "alex",
                "--date",
                "2026-08-01",
                "--flow",
                "medium",
                "--pain",
                "6",
                "--symptoms",
                "cramps,fatigue",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Logged daily entry for alex on 2026-08-01", out)

        # 8. predict
        code, out, _err = self.run_cli(["predict", "alex"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["predicted_cycle_length_days"], 29)

        # 9. history
        code, out, _err = self.run_cli(["history", "alex"])
        self.assertEqual(code, 0)
        history = json.loads(out)
        self.assertEqual(history["profile"], "alex")
        self.assertEqual(len(history["recent_period_starts"]), 1)
        self.assertEqual(len(history["recent_daily_logs"]), 1)

        # 10. profiles
        code, out, _err = self.run_cli(["profiles"])
        self.assertEqual(code, 0)
        self.assertIn("alex [role=cycler]", out)
        self.assertIn("sam [role=partner]", out)


class patch_argv:
    def __init__(self, argv):
        self.argv = argv
        self.orig_argv = None

    def __enter__(self):
        self.orig_argv = sys.argv
        sys.argv = self.argv

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.argv = self.orig_argv


if __name__ == "__main__":
    unittest.main()
