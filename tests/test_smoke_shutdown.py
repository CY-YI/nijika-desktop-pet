"""Check the isolated serve-only test process exits without a forced kill."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SmokeShutdownTests(unittest.TestCase):
    def test_serve_only_stops_on_its_private_signal(self):
        with tempfile.TemporaryDirectory(prefix="nijika-shutdown-test-") as directory:
            root = Path(directory)
            signal = root / "stop.signal"
            temp = root / "temp"
            temp.mkdir()
            database = root / "state" / "notifications.sqlite3"
            env = {**os.environ, "NIJIKA_PET_DB_PATH": str(database),
                   "TEMP": str(temp), "TMP": str(temp)}
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "control_panel.py"), "--serve-only",
                 "--agent-home", str(root / "user"), "--test-shutdown-file", str(signal)],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            try:
                status = database.parent / "panel-status.json"
                deadline = time.monotonic() + 15
                while not status.exists() and time.monotonic() < deadline:
                    if proc.poll() is not None:
                        self.fail(f"panel exited during startup: {proc.returncode}")
                    time.sleep(0.1)
                self.assertTrue(status.exists(), "isolated panel did not start")
                self.assertGreater(json.loads(status.read_text(encoding="utf-8"))["pid"], 0)
                signal.touch()
                self.assertEqual(proc.wait(timeout=10), 0)
                self.assertFalse(status.exists())
                self.assertFalse(list(temp.glob("_MEI*")))
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stderr:
                    proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
