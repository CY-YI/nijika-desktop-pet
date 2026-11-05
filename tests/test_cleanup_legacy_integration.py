import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.audit_agent_integrations import ROOT


@unittest.skipUnless(os.name == "nt", "Windows legacy cleanup smoke test")
class LegacyIntegrationCleanupTests(unittest.TestCase):
    def write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def run_script(self, *arguments: str) -> dict:
        result = subprocess.run(
            [
                "powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(ROOT / "tools/cleanup_legacy_nijika_integration.ps1"),
                *arguments,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_dry_run_changes_nothing_and_apply_backs_up_exact_targets(self):
        with tempfile.TemporaryDirectory(prefix="虹夏 legacy cleanup ") as directory:
            base = Path(directory)
            user = base / "收件人 User"
            codex = user / ".codex"
            data = user / ".nijika-desktop-pet"
            legacy = user / ".agents/skills/nijika-desktop-dialog/SKILL.md"
            other_skill = user / ".agents/skills/keep-me/SKILL.md"
            authority = codex / "skills/nijika-desktop-dialog/SKILL.md"
            obsolete_backup = codex / "skills/nijika-desktop-dialog/SKILL.md.bak-nijika-20261009-195053-238"
            probe = data / "codex-approval-probe-20261017-f9137c62.txt"
            backup = base / "backup"

            source = (ROOT / "skills/nijika-desktop-dialog/SKILL.md").read_bytes()
            self.write(authority, source)
            self.write(legacy, b"stale duplicate")
            self.write(other_skill, b"preserve me")
            self.write(obsolete_backup, b"obsolete")
            self.write(probe, b"")

            common = (
                "-UserProfile", str(user),
                "-CodexHome", str(codex),
                "-NijikaDataRoot", str(data),
                "-SourceRoot", str(ROOT),
            )
            plan = self.run_script(*common)
            self.assertEqual(plan["status"], "plan")
            self.assertEqual(len(plan["targets"]), 3)
            self.assertTrue(legacy.is_file())
            self.assertTrue(obsolete_backup.is_file())
            self.assertTrue(probe.is_file())

            applied = self.run_script(
                *common,
                "-Apply",
                "-BackupDirectory", str(backup),
            )
            self.assertEqual(applied["status"], "applied")
            self.assertFalse(legacy.parent.exists())
            self.assertFalse(obsolete_backup.exists())
            self.assertFalse(probe.exists())
            self.assertEqual(authority.read_bytes(), source)
            self.assertEqual(other_skill.read_bytes(), b"preserve me")
            manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["targets"]), 3)
            self.assertEqual(
                (backup / "01-nijika-desktop-dialog/SKILL.md").read_bytes(),
                b"stale duplicate",
            )


if __name__ == "__main__":
    unittest.main()
