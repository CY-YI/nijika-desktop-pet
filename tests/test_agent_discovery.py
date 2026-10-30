"""Real safety and routing boundaries of local discovery, all homes isolated."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_discovery import scan, read_json, magpie_state, MAX_CONFIG
from agent_setup import AgentSetup
from control_store import ControlStore
from notification_store import NotificationStore
from agent_activity import AgentActivity

ROOT = Path(__file__).resolve().parents[1]


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "user"
        self.home.mkdir()
        self.store = ControlStore(Path(self.temp.name) / "data/notifications.sqlite3")
        self.setup = AgentSetup(ROOT, self.store, self.home)

    def write(self, relative, value):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def service(self, **extra):
        return {"command": str(self.setup.mcp), "args": [], **extra}

    def manager(self, targets):
        return self.write(".config/magpie/library.json", {"mcp": [
            {"name": "nijika-pet", **self.service(), "agents": targets}]})

    def test_scan_is_bounded_readonly_sanitized_and_does_not_claim_connection(self):
        path = self.write(".gemini/settings.json", {"mcpServers": {
            "nijika-pet": self.service(), "other": {"env": {"PRIVATE": "not-for-discovery-output"}}}})
        before = {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        items = scan(self.home, self.setup.mcp, which=lambda _: None)
        item = next(i for i in items if i["id"] == "gemini")
        self.assertTrue(item["detected"])
        self.assertEqual(item["configuration"], "found")
        self.assertIn("尚未验证", item["verification"])
        self.assertNotIn("not-for-discovery-output", json.dumps(items))
        self.assertEqual(before, {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()})
        path.write_bytes(b"x" * (MAX_CONFIG + 1))
        self.assertTrue(next(i for i in scan(self.home, self.setup.mcp, which=lambda _: None)
                             if i["id"] == "gemini")["issue"])

    def test_duplicate_json_invalid_manager_and_oversize_block_safe_writes(self):
        path = self.write(".gemini/settings.json", {})
        path.write_text('{"mcpServers":{},"mcpServers":{}}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_json(path)
        with self.assertRaises(ValueError):
            self.setup.plan("gemini", "Gemini")
        manager = self.manager("gemini")
        self.assertTrue(magpie_state(self.home, "gemini")["error"])
        with self.assertRaises(ValueError):
            self.setup.plan("codex", "Codex")
        manager.write_bytes(b"x" * (MAX_CONFIG + 1))
        self.assertTrue(magpie_state(self.home, "codex")["error"])

    def test_all_three_json_adapters_preserve_other_settings_dedupe_and_are_idempotent(self):
        for client, relative, identity in (
            ("claude", ".claude.json", "Claude"),
            ("gemini", ".gemini/settings.json", "Gemini"),
            ("copilot", ".copilot/mcp-config.json", "Copilot"),
        ):
            with self.subTest(client=client):
                entry = self.service(env={"OTHER": "preserve"}, timeout=45)
                path = self.write(relative, {"other": [1, 2], "mcpServers": {
                    "nijika-pet": entry, "nijika_pet": entry, "other": {"command": "keep"}}})
                plan = self.setup.plan(client, client)
                self.assertEqual(len(plan["files"]), 2)
                result = self.setup.apply(plan["plan_id"])
                data = read_json(path)
                self.assertEqual(data["other"], [1, 2])
                self.assertEqual(data["mcpServers"]["other"], {"command": "keep"})
                self.assertNotIn("nijika_pet", data["mcpServers"])
                service = data["mcpServers"]["nijika-pet"]
                self.assertEqual(service["timeout"], 45)
                self.assertEqual(service["env"]["OTHER"], "preserve")
                self.assertEqual(service["env"]["NIJIKA_AGENT_NAME"], identity)
                self.assertEqual(service["env"]["NIJIKA_PROFILE_ID"], result["agent"]["id"])
                self.assertFalse(self.setup.plan(client, client)["files"])
                self.assertEqual(len(self.store.agents()), ("claude", "gemini", "copilot").index(client) + 1)

    def test_json_unknown_program_conflicting_alias_and_project_scope_refuse_without_write(self):
        for document in (
            {"mcpServers": {"nijika-pet": {"command": "unknown.exe"}}},
            {"mcpServers": {"nijika-pet": self.service(timeout=1), "nijika_pet": self.service(timeout=2)}},
            {"projects": {"project": {"mcpServers": {"nijika-pet": self.service()}}}},
        ):
            path = self.write(".claude.json", document)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                self.setup.plan("claude", "Claude")
            self.assertEqual(path.read_bytes(), before)

    def test_managed_client_registers_only_and_rechecks_ownership_at_apply(self):
        path = self.write(".gemini/settings.json", {"mcpServers": {"keep": {"command": "keep"}}})
        manager = self.manager(["gemini"])
        before = path.read_bytes()
        plan = self.setup.plan("gemini", "Gemini")
        self.assertEqual(plan["manager"], "magpie")
        self.assertFalse(plan["files"])
        result = self.setup.apply(plan["plan_id"])
        self.assertEqual(result["agent"]["status"], "managed")
        self.assertIn("本次不授权修改", result["agent"]["guide"]["prompt"])
        self.assertEqual(path.read_bytes(), before)
        plan = self.setup.plan("codex", "Codex")
        self.manager(["gemini", "codex"])
        with self.assertRaisesRegex(ValueError, "MAGPIE"):
            self.setup.apply(plan["plan_id"])
        self.assertFalse((self.home / ".codex/config.toml").exists())

    def test_batch_partial_failure_duplicate_invalid_selection_and_one_shot_apply(self):
        self.write(".claude.json", {"mcpServers": {"nijika-pet": {"command": "unknown.exe"}}})
        for selected in ([], ["codex", "codex"], ["unknown"], "codex", [None]):
            with self.assertRaises(ValueError):
                self.setup.batch_plan(selected)
        batch = self.setup.batch_plan(["claude", "gemini", "copilot"])
        self.assertEqual([item["status"] for item in batch["results"]], ["blocked", "ready", "ready"])
        result = self.setup.batch_apply(batch["batch_id"])
        self.assertEqual([item["status"] for item in result["results"]], ["blocked", "configured", "configured"])
        self.assertEqual(len(self.store.agents()), 2)
        with self.assertRaises(ValueError):
            self.setup.batch_apply(batch["batch_id"])

    def test_batch_file_changed_after_preview_is_failed_independently(self):
        batch = self.setup.batch_plan(["claude", "gemini"])
        path = self.write(".claude.json", {"changed": True})
        result = self.setup.batch_apply(batch["batch_id"])
        self.assertEqual([i["status"] for i in result["results"]], ["failed", "configured"])
        self.assertEqual(read_json(path), {"changed": True})

    def test_json_changed_during_plan_cannot_become_the_new_backup_baseline(self):
        from setup_config import json_service_update
        path = self.write(".gemini/settings.json", {"original": True})
        def changed(*args):
            result = json_service_update(*args)
            path.write_text('{"changed":true}', encoding="utf-8")
            return result
        with patch("agent_setup.json_service_update", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "其他程序"):
                self.setup.plan("gemini", "Gemini")
        self.assertEqual(read_json(path), {"changed": True})

    def test_isolated_home_does_not_follow_real_environment_overrides(self):
        with patch.dict(os.environ, {"CODEX_HOME": "C:/outside", "COPILOT_HOME": "C:/outside"}):
            self.assertEqual(self.setup.default_home("codex"), self.home / ".codex")
            self.assertEqual(self.setup.default_home("copilot"), self.home / ".copilot")
        with patch.dict(os.environ, {"CODEX_HOME": "C:/outside"}):
            relative = AgentSetup(ROOT, self.store, Path("."))
            self.assertEqual(relative.default_home("codex"), Path.cwd() / ".codex")

    def test_guided_managed_client_does_not_generate_conflicting_write_instructions(self):
        self.manager(["workbuddy"])
        plan = self.setup.plan("custom", "WorkBuddy", software="WorkBuddy")
        self.assertEqual(plan["manager"], "magpie")
        self.assertIn("本次不授权修改", plan["guide"]["prompt"])
        self.assertNotIn("【请自动执行】", plan["guide"]["prompt"])
        result = self.setup.apply(plan["plan_id"])
        repeated = self.setup.plan("custom", "WorkBuddy", software="WorkBuddy")
        self.assertEqual(self.setup.plans[repeated["plan_id"]]["id"], result["agent"]["id"])

    def test_simultaneous_managed_previews_cannot_register_duplicate_profiles(self):
        self.manager(["gemini"])
        first = self.setup.plan("gemini", "First")
        second = self.setup.plan("gemini", "Second")
        self.setup.apply(first["plan_id"])
        with self.assertRaisesRegex(ValueError, "重复登记"):
            self.setup.apply(second["plan_id"])
        self.assertEqual(len(self.store.agents()), 1)

    def test_panel_click_does_not_create_host_activity_and_legacy_rows_still_work(self):
        queue = NotificationStore(self.store.database)
        activity = AgentActivity(self.store.database)
        profile = "a" * 32
        notice = queue.create("ChatGPT", "本机测试", "面板测试不能证明宿主调用。", ("收到",))
        queue.answer(notice.id, 0)
        self.assertFalse(activity.snapshot(profile)["called"])
        activity.record(profile, notice.id)
        self.assertTrue(activity.snapshot(profile)["answered"])
        self.assertFalse(activity.snapshot("b" * 32)["called"])
        activity.record("../bad", notice.id)
        # Original nine-column insert remains compatible with old live clients.
        with queue._connect() as connection:
            connection.execute("INSERT INTO notifications VALUES (?,?,?,?,?,?,?,?,?)",
                               ("b" * 32, "old", "test", "test", '["OK"]', "pending", None, 1, 1))
        self.assertEqual(queue.get("b" * 32).agent, "old")


if __name__ == "__main__":
    unittest.main()
