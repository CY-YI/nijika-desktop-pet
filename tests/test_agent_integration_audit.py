import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.audit_agent_integrations import ROOT, audit


class AgentIntegrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "user"
        environment = patch.dict(
            "os.environ", {"CODEX_HOME": str(self.home / ".codex")})
        environment.start()
        self.addCleanup(environment.stop)
        self.source = ROOT / "skills/nijika-desktop-dialog/SKILL.md"
        self.primary = self.home / ".codex/skills/nijika-desktop-dialog/SKILL.md"
        self.legacy = self.home / ".agents/skills/nijika-desktop-dialog/SKILL.md"

    def install(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def codex_row(self, result: dict) -> dict:
        return next(item for item in result["skills"] if item["client"] == "Codex")

    def test_matching_skill_copy_is_clean(self):
        self.install(self.primary, self.source.read_bytes())

        result = audit(self.home)

        self.assertEqual(result["status"], "clean")
        self.assertEqual(self.codex_row(result)["status"], "clean")

    def test_stale_skill_copy_is_a_conflict(self):
        self.install(self.primary, self.source.read_bytes())
        self.install(self.legacy, b"stale duplicate")

        result = audit(self.home)

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["issues"][0]["kind"], "content_mismatch")
        self.assertEqual(result["issues"][0]["path"], str(self.legacy))

    def test_two_matching_skill_copies_are_a_duplicate(self):
        data = self.source.read_bytes()
        self.install(self.primary, data)
        self.install(self.legacy, data)

        result = audit(self.home)

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["issues"][0]["kind"], "duplicate_skill")
        self.assertEqual(self.codex_row(result)["status"], "duplicate")


if __name__ == "__main__":
    unittest.main()
