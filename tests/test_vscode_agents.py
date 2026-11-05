import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import mcp_server
from agent_discovery import scan
from agent_setup import AgentSetup
from control_store import ControlStore
from host_process import from_ancestry
from notice_source import notification_source, task_heading
from vscode_agents import discover, ROUTES

ROOT = Path(__file__).resolve().parents[1]


class EditorRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.setup = AgentSetup(ROOT, ControlStore(Path(self.temp.name) / "data/db.sqlite3"), self.home)

    def write(self, path, data):
        path = self.home / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_manifest_detection_deduplicates_versions_without_reading_settings(self):
        for extension_id in ROUTES:
            publisher, name = extension_id.split(".", 1)
            for version in ("1.0", "2.0"):
                self.write(f".vscode/extensions/{extension_id}-{version}/package.json",
                           {"publisher": publisher, "name": name, "private": "not-returned"})
        self.write(".vscode/extensions/openai.chatgpt-3.0/package.json", {"publisher": "wrong", "name": "chatgpt"})
        routes = discover(self.home)
        self.assertEqual(len(routes), len(ROUTES))
        self.assertEqual({r["identity"] for r in routes}, {v[0] for v in ROUTES.values()})
        self.assertNotIn("not-returned", json.dumps(routes))
        items = scan(self.home, self.setup.mcp, which=lambda _: None)
        self.assertEqual(len([r for r in items if r.get("extension_id")]), len(ROUTES))
        self.assertTrue(all(r["configuration"] == "not_verified" for r in routes))

    def test_ancestry_is_bounded_and_does_not_mislabel_terminal_tasks(self):
        self.assertEqual(from_ancestry({1: (2, "mcp.exe"), 2: (3, "node.exe"),
                                       3: (0, "Code.exe")}, 1), "VS Code")
        self.assertEqual(from_ancestry({1: (2, "mcp.exe"), 2: (3, "pwsh.exe"),
                                       3: (0, "Code.exe")}, 1), "")
        self.assertEqual(from_ancestry({1: (2, "mcp.exe"), 2: (1, "node.exe")}, 1), "")
        self.assertEqual(from_ancestry({1: (0, "Code - Insiders.exe")}, 1), "VS Code Insiders")
        self.assertEqual(from_ancestry({1: (0, "Cursor.exe")}, 1), "")

    def test_editor_route_installs_conditional_rule_without_relabelling_shared_mcp(self):
        path = self.home / ".codex/config.toml"
        path.parent.mkdir()
        original = '[mcp_servers.other]\ncommand = "keep.exe"\n'
        path.write_text(original, encoding="utf-8")
        plan = self.setup.plan("custom", "编辑器", str(self.home), "Codex", "VS Code")
        self.assertEqual(len(plan["files"]), 1)
        result = self.setup.apply(plan["plan_id"])
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        instructions = (self.home / ".codex/AGENTS.md").read_text(encoding="utf-8")
        self.assertIn('agent_name="Codex"', instructions)
        self.assertIn("仅当当前任务确实运行在 VS Code", instructions)
        self.assertIn("不要把共享配置中的 NIJIKA_HOST_NAME 全局改成 VS Code", instructions)
        prompt = result["agent"]["guide"]["prompt"]
        self.assertIn(str(path), prompt)
        self.assertIn('software="VS Code"', prompt)
        self.assertIn("不得覆盖共享配置", prompt)
        self.assertEqual(self.setup.plan("custom", "编辑器", str(self.home), "Codex", "VS Code")["files"], [])

    def test_managed_backend_is_not_written_and_unknown_extension_is_guidance_only(self):
        self.write(".config/magpie/library.json", {"mcp": [{"name": "nijika-pet",
            "command": str(self.setup.mcp), "agents": ["codex"]}]})
        plan = self.setup.plan("custom", "编辑器", str(self.home), "Codex", "VS Code")
        self.assertEqual(plan["manager"], "magpie")
        self.assertFalse(plan["files"])
        self.assertIn('agent_name="Codex"', plan["guide"]["prompt"])
        self.assertFalse(self.setup.plan("custom", "编辑器", str(self.home), "CodeBuddy", "VS Code")["files"])

    def test_insiders_and_stable_rules_coexist(self):
        for software in ("VS Code", "VS Code Insiders"):
            plan = self.setup.plan("custom", software, str(self.home), "Claude Code", software)
            self.setup.apply(plan["plan_id"])
        text = (self.home / ".claude/CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn('software="VS Code"', text)
        self.assertIn('software="VS Code Insiders"', text)

    def test_editor_rules_changed_after_preview_are_not_overwritten(self):
        rules = self.home / ".codex/AGENTS.md"
        rules.parent.mkdir()
        rules.write_text("original", encoding="utf-8")
        plan = self.setup.plan("custom", "编辑器", str(self.home), "Codex", "VS Code")
        rules.write_text("user-edited", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.setup.apply(plan["plan_id"])
        self.assertEqual(rules.read_text(encoding="utf-8"), "user-edited")

    def test_process_source_and_explicit_override_do_not_pollute_other_hosts(self):
        context = lambda name: SimpleNamespace(session=SimpleNamespace(
            client_params=SimpleNamespace(client_info=SimpleNamespace(name=name))))
        with patch.object(mcp_server, "EDITOR_HOST", "VS Code"), \
                patch.object(mcp_server, "AGENT_NAME", "auto"), patch.object(mcp_server, "HOST_NAME", ""):
            for caller, identity in (("codex-mcp-client", "Codex"), ("claude-code", "Claude Code")):
                source = mcp_server.request_source(context(caller))
                self.assertEqual(source.heading, "VS Code · " + identity)
                self.assertEqual(task_heading(source.heading + " · 修复问题", source), "修复问题")
            self.assertEqual(mcp_server.request_source(context("dsh-mcp-client")).heading, "Agent · DSH")
            self.assertEqual(mcp_server.request_source(context("codex"), "ChatGPT", "Work").heading, "ChatGPT · Work")
        with patch.object(mcp_server, "EDITOR_HOST", ""), \
                patch.object(mcp_server, "AGENT_NAME", "auto"), patch.object(mcp_server, "HOST_NAME", ""):
            self.assertEqual(mcp_server.request_source(context("codex")).heading, "ChatGPT · Codex")
        for identity in ("Codex", "Claude Code", "DSH", "CodeBuddy"):
            self.assertEqual(notification_source(identity, "VS Code").heading, "VS Code · " + identity)


if __name__ == "__main__":
    unittest.main()
