"""Regressions from the real frontend setup audit, using isolated client homes."""
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest

from agent_setup import AgentSetup, remove_legacy_dsh_nijika_entry
from control_store import ControlStore
from setup_config import codex_service_update, json_service_update, repair_orphan_dsh_marker

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ("    - id: magpie-mcp-nijika-pet\n"
          "      name: '@deepseek-ai/dsh-mcp-client'\n"
          "      config:\n        serverName: nijika_pet\n        command: 'old.exe'\n")
OTHER = "    - id: unrelated-service\n      name: keep-this-service\n      config: {}\n"


class SetupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.store = ControlStore(self.home / "state/notifications.sqlite3")
        self.setup = AgentSetup(ROOT, self.store, self.home)
        self.codex = self.home / ".codex/config.toml"
        self.codex.parent.mkdir()

    def test_dsh_siblings_order_multiple_blocks_and_markers_preserved(self):
        for before, after in (("", OTHER), (OTHER, ""), (OTHER, OTHER.replace("unrelated", "second"))):
            for eol in ("\n", "\r\n"):
                text = ("# header\n- insert:\n    # magpie\n" + before + LEGACY + after +
                        "# BEGIN NIJIKA-DSH-MCP\n- insert:\n    - id: mcp-nijika-pet\n"
                        "      config: {}\n# END NIJIKA-DSH-MCP\n- remove: other\n").replace("\n", eol)
                result = remove_legacy_dsh_nijika_entry(text)
                self.assertNotIn("magpie-mcp-nijika-pet", result)
                self.assertIn((before + after).replace("\n", eol), result)
                self.assertIn("# BEGIN NIJIKA-DSH-MCP", result)
                self.assertIn("- remove: other", result)
                self.assertEqual(remove_legacy_dsh_nijika_entry(result), result)

    def test_dsh_unsupported_or_unknown_target_refused(self):
        for text in ("- insert: [{id: magpie-mcp-nijika-pet}]",
                     "- insert:\n" + LEGACY.replace("nijika_pet", "unrelated"),
                     "- insert:\n" + LEGACY + "      description: |\n        literal\n"):
            with self.assertRaises(ValueError):
                remove_legacy_dsh_nijika_entry(text)

    def test_dsh_orphan_marker_is_removed_without_touching_managed_or_paired_blocks(self):
        orphan = "# keep\n# BEGIN NIJIKA-DSH-MCP\n- insert:\n    - id: keep\n"
        repaired = repair_orphan_dsh_marker(orphan)
        self.assertNotIn("# BEGIN NIJIKA-DSH-MCP", repaired)
        self.assertIn("- insert:\n    - id: keep", repaired)
        managed = orphan + "      id: mcp-nijika-pet\n"
        self.assertEqual(repair_orphan_dsh_marker(managed), managed)
        paired = orphan + "# END NIJIKA-DSH-MCP\n"
        self.assertEqual(repair_orphan_dsh_marker(paired), paired)

    def test_magpie_managed_dsh_repairs_only_orphan_marker_and_never_rewrites_service(self):
        manager = self.home / ".config/magpie/library.json"
        manager.parent.mkdir(parents=True)
        manager.write_text(json.dumps({"mcp": [{
            "name": "nijika-pet", "command": str(self.setup.mcp), "args": [],
            "agents": ["dsh"],
        }]}), encoding="utf-8")
        for profile in ("desktop", "web"):
            path = self.home / ".dsh/profiles" / profile / "cordis.patch.yml"
            path.parent.mkdir(parents=True)
            path.write_text("# keep\n# BEGIN NIJIKA-DSH-MCP\n- insert:\n    - id: keep\n",
                            encoding="utf-8")
        plan = self.setup.plan("dsh", "助手")
        self.assertEqual(plan["manager"], "magpie")
        self.assertEqual(len(plan["files"]), 2)
        self.setup.apply(plan["plan_id"])
        for profile in ("desktop", "web"):
            value = (self.home / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
            self.assertEqual(value, "# keep\n- insert:\n    - id: keep\n")

    def test_dsh_plan_and_apply_preserve_sibling_and_backup(self):
        text = "# user patch\n- insert:\n" + LEGACY + OTHER
        for profile in ("desktop", "web"):
            path = self.home / ".dsh/profiles" / profile / "cordis.patch.yml"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
        plan = self.setup.plan("dsh", "助手")
        result = self.setup.apply(plan["plan_id"])
        for profile in ("desktop", "web"):
            updated = (self.home / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
            self.assertIn(OTHER, updated)
            self.assertNotIn("magpie-mcp-nijika-pet", updated)
            self.assertEqual(updated.count("id: mcp-nijika-pet"), 1)
        self.assertTrue(any(Path(p).read_text(encoding="utf-8") == text for p in result["agent"]["backups"]))
        self.assertEqual(self.setup.plan("dsh", "助手")["files"], [])

    def entry(self, name="nijika-pet", command=None, extra=""):
        return (f'[mcp_servers."{name}"] # original comment\ncommand = ' +
                json.dumps(str(command or self.setup.mcp), ensure_ascii=False) + "\n" +
                extra + f'[mcp_servers."{name}".env]\nNIJIKA_AGENT_NAME = "DSH"\n')

    def test_codex_quoted_alias_consolidation_preserves_options_and_unrelated(self):
        prefix = '[mcp_servers.other]\ncommand = "other.exe"\nenabled = false\n'
        options = 'enabled = false\ntool_timeout_sec = 180\n'
        self.codex.write_text(prefix + self.entry("nijika_pet", extra=options) +
                              self.entry(extra=options), encoding="utf-8")
        original = self.codex.read_bytes()
        result = self.setup.apply(self.setup.plan("codex", "伙伴")["plan_id"])
        after = tomllib.loads(self.codex.read_text(encoding="utf-8"))
        self.assertEqual(set(after["mcp_servers"]), {"other", "nijika-pet"})
        self.assertFalse(after["mcp_servers"]["nijika-pet"]["enabled"])
        self.assertEqual(after["mcp_servers"]["nijika-pet"]["tool_timeout_sec"], 180)
        self.assertEqual(after["mcp_servers"]["other"], {"command": "other.exe", "enabled": False})
        self.assertTrue(any(Path(p).read_bytes() == original for p in result["agent"]["backups"]))
        self.assertEqual(self.setup.plan("codex", "伙伴")["files"], [])

    def test_codex_conflicting_alias_unknown_program_and_inline_refuse_without_writes(self):
        bad = self.home / "old-version/虹夏MCP-v2.exe"
        bad.parent.mkdir()
        bad.write_bytes(b"unverified old program")
        for text in (self.entry(command=bad), self.entry() + self.entry("nijika_pet", extra="enabled = false\n"),
                     '[mcp_servers]\nnijika_pet = { command = ' + json.dumps(str(self.setup.mcp)) + ' }\n'):
            self.codex.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.setup.plan("codex", "伙伴")
            self.assertEqual(self.codex.read_text(encoding="utf-8"), text)

    def test_codex_identical_old_program_relocated_and_preview_is_explicit(self):
        old = self.home / "old/虹夏MCP-v2.exe"
        old.parent.mkdir()
        shutil.copyfile(self.setup.mcp, old)
        self.codex.write_text(self.entry(command=old), encoding="utf-8")
        plan = self.setup.plan("codex", "伙伴")
        self.assertIn(str(old), "\n".join(plan["notes"]))
        self.assertIn(str(self.setup.mcp), "\n".join(plan["notes"]))
        self.setup.apply(plan["plan_id"])
        self.assertEqual(tomllib.loads(self.codex.read_text(encoding="utf-8"))["mcp_servers"]["nijika-pet"]["command"],
                         str(self.setup.mcp))

    def test_known_legacy_onefile_paths_migrate_even_after_old_binary_is_removed(self):
        application = self.home / "application"
        current = application / "dist/虹夏MCP-v2/虹夏MCP-v2.exe"
        current.parent.mkdir(parents=True)
        current.write_bytes(b"current onedir executable")
        legacy = application / "dist/虹夏MCP-v2.exe"
        codex = (
            '[mcp_servers.nijika-pet]\ncommand = ' + json.dumps(str(legacy)) +
            '\n[mcp_servers.nijika-pet.env]\nNIJIKA_AGENT_NAME = "Codex"\n'
        )
        updated, notes = codex_service_update(
            codex, current, application, {}, lambda text, environment: text)
        self.assertEqual(
            tomllib.loads(updated)["mcp_servers"]["nijika-pet"]["command"],
            str(current),
        )
        self.assertTrue(notes)

        document = {"mcpServers": {"nijika-pet": {"command": str(legacy)}}}
        migrated = json_service_update(
            document, current, {"NIJIKA_AGENT_NAME": "Claude"},
            "claude", application)
        self.assertEqual(migrated["mcpServers"]["nijika-pet"]["command"], str(current))

    def test_custom_source_required_and_consistent_across_saved_handoff(self):
        for software in ("", "auto", "未识别软件", "bad\nhost"):
            with self.assertRaises(ValueError):
                self.setup.plan("custom", "伙伴", software=software)
        plan = self.setup.plan("custom", "可以超过二十字的管理昵称这里只影响档案名称", agent_identity="Claude", software="VS Code")
        env = plan["export"]["mcpServers"]["nijika-pet"]["env"]
        self.assertEqual(env, {"NIJIKA_AGENT_NAME": "Claude", "NIJIKA_HOST_NAME": "VS Code",
                               "NIJIKA_PROFILE_ID": self.setup.plans[plan["plan_id"]]["id"]})
        result = self.setup.apply(plan["plan_id"])
        saved = self.store.agent(result["agent"]["id"])
        self.assertEqual(self.setup.export_agent(saved), plan["export"])
        self.assertIn('"NIJIKA_HOST_NAME": "VS Code"', self.setup.describe(saved)["guide"]["prompt"])
        self.assertEqual(self.setup.plan("custom", "未知模型", software="WorkBuddy")["export"]["mcpServers"]["nijika-pet"]["env"]["NIJIKA_AGENT_NAME"],
                         "Agent")


if __name__ == "__main__":
    unittest.main()
