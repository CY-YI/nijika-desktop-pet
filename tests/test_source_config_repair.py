import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from tools.repair_nijika_sources import patch_json, patch_library, patch_toml, patch_dsh, run


class SourceConfigRepairTests(unittest.TestCase):
    def setUp(self):
        self.server = {"command": "C:/Apps/虹夏MCP-v2.exe", "env": {"NIJIKA_AGENT_NAME": "DSH"}}

    def test_json_scopes_preserve_unrelated_and_converge(self):
        original = {"mcpServers": {"nijika-pet": self.server, "nijika_pet": self.server,
                                   "other": {"command": "other.exe"}},
                    "projects": {"folder": {"mcpServers": {"nijika_pet": self.server}}},
                    "permissions": {"mode": "keep"}}
        result, fragments = patch_json(json.dumps(original), "Gemini CLI")
        parsed = json.loads(result)
        self.assertEqual(len(fragments), 2)
        self.assertEqual(len(parsed["mcpServers"]), 2)
        self.assertEqual(parsed["permissions"], original["permissions"])
        self.assertEqual(parsed["mcpServers"]["other"], original["mcpServers"]["other"])
        self.assertEqual(parsed["mcpServers"]["nijika-pet"]["env"],
                         {"NIJIKA_AGENT_NAME": "Gemini", "NIJIKA_HOST_NAME": "Gemini CLI"})
        self.assertEqual(patch_json(result, "Gemini CLI")[0], result)

    def test_library_neutral_single_service_and_scoped_skills(self):
        first = {**self.server, "name": "nijika-pet", "agents": ["codex", "gemini"]}
        second = {**self.server, "name": "nijika_pet", "agents": ["dsh"]}
        original = {"mcp": [first, second, {"name": "other", "command": "other.exe"}],
                    "skills": [{"name": "nijika-desktop-dialog", "agents": ["codex", "dsh"]},
                               {"name": "nijika-dsh-dialog", "agents": ["codex", "dsh"]}],
                    "extra": {"value": "untouched"}}
        result, fragments = patch_library(json.dumps(original))
        parsed = json.loads(result)
        self.assertEqual(parsed["mcp"][-1]["env"], {"NIJIKA_AGENT_NAME": "auto"})
        self.assertEqual(parsed["mcp"][-1]["agents"], ["codex", "dsh", "gemini"])
        self.assertEqual(parsed["skills"][0]["agents"], ["codex"])
        self.assertEqual(parsed["skills"][1]["agents"], ["dsh"])
        self.assertEqual(parsed["extra"], original["extra"])
        self.assertEqual(patch_library(result)[0], result)

    def test_toml_inline_and_tables_preserve_options_and_comments(self):
        for env in ('env = { NIJIKA_AGENT_NAME = "DSH" }',
                    '[mcp_servers.nijika-pet.env]\nNIJIKA_AGENT_NAME = "DSH"'):
            original = ('# keep\n[other]\nsetting = "unchanged"\n[mcp_servers.nijika-pet]\n'
                        'command = "C:/Apps/虹夏MCP-v2.exe"\nstartup_timeout_sec = 50\n' + env +
                        '\n[mcp_servers.nijika_pet]\ncommand = "C:/Apps/虹夏MCP-v2.exe"\n'
                        '[mcp_servers.nijika_pet.env]\nNIJIKA_AGENT_NAME = "Claude code"\n')
            result, _ = patch_toml(original, "Codex")
            self.assertIn("# keep", result)
            self.assertIn('startup_timeout_sec = 50', result)
            self.assertNotIn("[mcp_servers.nijika_pet]", result)
            self.assertIn('NIJIKA_HOST_NAME = "Codex"', result)
            self.assertEqual(patch_toml(result, "Codex")[0], result)

    def test_new_setup_replaces_stale_host_without_duplicate_env_table(self):
        import tomllib
        from agent_setup import normalize_codex_environment
        for body in ('env = { NIJIKA_HOST_NAME = "Work", KEEP = "value" } # keep comment',
                     '[mcp_servers.nijika-pet.env]\nNIJIKA_HOST_NAME = "Work"\nKEEP = "value"'):
            text = '[mcp_servers.nijika-pet]\ncommand = "pet.exe"\n' + body + '\n'
            result = normalize_codex_environment(text, {"NIJIKA_AGENT_NAME": "ChatGPT", "NIJIKA_HOST_NAME": "Codex"})
            data = tomllib.loads(result)
            self.assertEqual(data["mcp_servers"]["nijika-pet"]["env"],
                             {"NIJIKA_AGENT_NAME": "ChatGPT", "NIJIKA_HOST_NAME": "Codex", "KEEP": "value"})
            self.assertEqual(normalize_codex_environment(result, {"NIJIKA_AGENT_NAME": "ChatGPT", "NIJIKA_HOST_NAME": "Codex"}), result)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "Optional audit-only PyYAML unavailable")
    def test_dsh_preserves_unrelated_insert_inside_historical_markers(self):
        import yaml
        text = ('- id: pet\n  disabled: true\n# BEGIN NIJIKA-DSH-MCP\n'
                '- insert: # magpie\n    - id: other\n      config:\n        command: other.exe\n')
        for alias in ("nijika_pet", "nijika-pet"):
            text += yaml.safe_dump([{"insert": [{"id": "magpie-mcp-" + alias, "config": self.server}]}], allow_unicode=True)
        result, _ = patch_dsh(text, "DSH")
        self.assertEqual(len(yaml.safe_load(result)), 3)
        self.assertIn("command: other.exe", result)
        self.assertEqual(patch_dsh(result, "DSH")[0], result)

    def test_read_only_and_fragment_only_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            target = home / ".gemini/settings.json"
            target.parent.mkdir()
            original = json.dumps({"mcpServers": {"nijika_pet": self.server},
                                   "unrelated": {"private_setting": "must-stay-local"}})
            target.write_text(original, encoding="utf-8")
            run(home)
            self.assertEqual(target.read_text(), original)
            backup = home / "backup"
            report = run(home, True, backup)
            self.assertFalse(any("error" in v for v in report))
            self.assertNotIn("must-stay-local", "".join(p.read_text() for p in backup.iterdir()))
            self.assertEqual(json.loads(target.read_text())["unrelated"]["private_setting"], "must-stay-local")
