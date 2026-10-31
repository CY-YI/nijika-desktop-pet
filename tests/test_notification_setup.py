"""Notification exports and lifecycle installation must be honest and isolated."""
import json
import tempfile
import unittest
from pathlib import Path

from agent_setup import AgentSetup, dsh_lifecycle_block, marked_block
from control_store import ControlStore
from notification_capabilities import notification_capability

ROOT = Path(__file__).resolve().parents[1]


class NotificationSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="虹夏 notification ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "user"
        self.home.mkdir()
        self.store = ControlStore(self.base / "data/queue.sqlite3")
        self.setup = AgentSetup(ROOT, self.store, self.home)
        for profile in ("desktop", "web"):
            path = self.home / ".dsh/profiles" / profile / "cordis.patch.yml"
            path.parent.mkdir(parents=True)
            path.write_text("# unrelated remains\n", encoding="utf-8")

    def test_reliability_never_confuses_available_with_verified(self):
        for client in ("codex", "dsh", "work", "claude", "gemini", "custom"):
            capability = notification_capability(client)
            self.assertFalse(capability["automatic_completion_verified"])
            self.assertEqual(capability["mode"],
                             "event_available" if client in {"codex", "dsh"} else "active_only")
        agent = {"id": "f" * 32, "client": "dsh", "name": "fixture", "source_name": "DSH",
                 "location": str(self.home / ".dsh")}
        info = self.setup.prepare_files(agent)
        manifest = json.loads((Path(info["bundle_directory"]) /
                               "nijika-notification-capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["lifecycle_executable"], str(ROOT / "dist/虹夏审批提醒.exe"))
        self.assertIn("不得让模型伪造", info["guide"]["prompt"])

    def test_dsh_plan_installs_one_lifecycle_block_and_is_idempotent(self):
        result = self.setup.apply(self.setup.plan("dsh", "fixture")["plan_id"])
        self.assertIn("agent", result)
        before = {}
        for profile in ("desktop", "web"):
            path = self.home / ".dsh/profiles" / profile / "cordis.patch.yml"
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# unrelated remains"))
            self.assertEqual(text.count("id: nijika-lifecycle-bridge"), 1)
            self.assertIn((ROOT / "integrations/dsh/lifecycle-bridge.mjs").as_uri(), text)
            before[path] = path.read_bytes()
        self.setup.apply(self.setup.plan("dsh", "fixture")["plan_id"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_invalid_second_profile_fails_before_writes(self):
        bad = self.home / ".dsh/profiles/web/cordis.patch.yml"
        bad.write_text("# BEGIN NIJIKA-DSH-LIFECYCLE\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        with self.assertRaises(ValueError):
            self.setup.plan("dsh", "fixture")
        self.assertEqual(before, {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()})
        with self.assertRaises(ValueError):
            marked_block("# B\n# E\n# B\n# E", "block", "# B", "# E")

    def test_recipient_paths_and_missing_component(self):
        root = self.base / "另一台电脑 安装目录"
        with self.assertRaises(ValueError):
            dsh_lifecycle_block(root)
        for name in ("integrations/dsh/lifecycle-bridge.mjs", "dist/虹夏审批提醒.exe"):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
        block = dsh_lifecycle_block(root)
        self.assertIn((root / "integrations/dsh/lifecycle-bridge.mjs").as_uri(), block)
        self.assertIn(str(root / "dist/虹夏审批提醒.exe"), block)
        self.assertNotIn(str(ROOT), block)

    def test_magpie_owned_dsh_is_not_silently_overwritten(self):
        from agent_discovery import magpie_state
        manager = self.home / ".config/magpie/library.json"
        manager.parent.mkdir(parents=True)
        manager.write_text(json.dumps({"mcp": [{"name": "nijika-pet", "command": str(self.setup.mcp),
                                               "agents": ["dsh"]}]}), encoding="utf-8")
        # Reuse the actual ownership parser rather than mocking an enabled service.
        state = magpie_state(self.home, "dsh")
        self.assertTrue(state["managed"])
        plan = self.setup.plan("dsh", "managed")
        self.assertEqual(plan["manager"], "magpie")
        self.assertFalse(any("cordis.patch.yml" in item["path"] for item in plan["files"]))
        self.assertIn("待独立验收", plan["guide"]["prompt"])
