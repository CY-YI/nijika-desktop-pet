import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import cleanup_mcp_temp


class McpTempCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def runtime(self, name: str = "_MEIowned"):
        directory = self.root / name
        directory.mkdir()
        for filename in cleanup_mcp_temp.RUNTIME_FILE_FINGERPRINT:
            (directory / filename).write_bytes(b"x")
        for dirname in cleanup_mcp_temp.RUNTIME_DIRECTORY_FINGERPRINT:
            (directory / dirname).mkdir()
        old = time.time() - 48 * 3600
        os.utime(directory, (old, old))
        return directory

    def test_dry_run_and_apply_only_remove_stale_fingerprinted_directories(self):
        eligible = self.runtime()
        unrelated = self.root / "_MEIunrelated"
        unrelated.mkdir()
        (unrelated / "python312.dll").write_bytes(b"x")
        (unrelated / "base_library.zip").write_bytes(b"x")
        recent = self.root / "_MEIrecent"
        recent.mkdir()
        for filename in cleanup_mcp_temp.RUNTIME_FILE_FINGERPRINT:
            (recent / filename).write_bytes(b"x")
        for dirname in cleanup_mcp_temp.RUNTIME_DIRECTORY_FINGERPRINT:
            (recent / dirname).mkdir()
        active = self.runtime("_MEIactive")

        with patch.object(cleanup_mcp_temp, "_windows_temp_roots_from_modules",
                          return_value={active}):
            candidates = cleanup_mcp_temp.scan(self.root, 24, {active})
        self.assertEqual([Path(item.path) for item in candidates if item.eligible], [eligible])
        self.assertTrue(eligible.exists())

        deleted, failed = cleanup_mcp_temp.apply(candidates, self.root)
        self.assertEqual(deleted, [str(eligible)])
        self.assertEqual(failed, [])
        self.assertFalse(eligible.exists())
        self.assertTrue(active.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(recent.exists())

    def test_fingerprint_without_all_runtime_markers_is_never_eligible(self):
        directory = self.root / "_MEIpartial"
        directory.mkdir()
        (directory / "python312.dll").write_bytes(b"x")
        old = time.time() - 48 * 3600
        os.utime(directory, (old, old))
        candidate = cleanup_mcp_temp.scan(self.root, 24, set())[0]
        self.assertFalse(candidate.eligible)
        self.assertEqual(candidate.reason, "runtime fingerprint mismatch")

    def test_summary_only_dry_run_reports_totals_without_paths(self):
        eligible = self.runtime()
        report_path = self.root / "report.json"
        arguments = [
            "cleanup_mcp_temp.py", "--temp-root", str(self.root),
            "--min-age-hours", "24", "--summary-only", "--output", str(report_path),
        ]
        with patch.object(cleanup_mcp_temp, "_windows_temp_roots_from_modules", return_value=set()), \
                patch.object(sys, "argv", arguments), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cleanup_mcp_temp.main(), 0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["eligible_directories"], 1)
        self.assertNotIn("directories", report)
        self.assertTrue(eligible.exists())


if __name__ == "__main__":
    unittest.main()
