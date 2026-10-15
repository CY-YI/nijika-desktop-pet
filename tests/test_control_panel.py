"""Meaningful isolation, conflict, image-pack and local API boundary tests."""
from __future__ import annotations

import io
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from PIL import Image, ImageDraw
from agent_setup import AgentSetup
from control_panel import ControlApplication, ControlServer
from control_store import ControlStore, SPRITES

ROOT = Path(__file__).resolve().parents[1]


def transparent_png():
    image = Image.new("RGBA", (100, 150))
    ImageDraw.Draw(image).ellipse((20, 20, 80, 130), fill="#ffc966")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class ControlStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "state/notifications.sqlite3"
        self.store = ControlStore(self.path)

    def test_settings_validate_and_preserve_unrelated_fields_across_instances(self):
        first = self.store.update_settings({"width": 380, "chat_enabled": False})
        other = ControlStore(self.path)
        second = other.update_settings({"motion": "gentle"})
        self.assertEqual(second["width"], 380)
        self.assertFalse(second["chat_enabled"])
        self.assertGreater(second["revision"], first["revision"])
        for patch in ({"width": True}, {"width": 999}, {"chat_enabled": "false"}, {"secret": "YOUR_API_KEY_HERE"}):
            with self.assertRaises(ValueError):
                self.store.update_settings(patch)
        self.assertEqual(self.store.settings(), second)

    def test_static_skin_and_expression_pack_switch_with_default_recovery(self):
        png = transparent_png()
        skin = self.store.import_skin(png, "试用外观.png")
        self.assertEqual(skin["kind"], "static")
        self.store.update_settings({"skin": skin["id"]})
        self.assertEqual(len(list(self.store.skin_directory(skin["id"]).glob("*.png"))), 9)
        archive = io.BytesIO()
        with ZipFile(archive, "w") as output:
            for name in SPRITES:
                output.writestr("skin/" + name + ".png", png)
        pack = self.store.import_skin(archive.getvalue(), "表情套装.zip")
        self.assertEqual(pack["kind"], "expressions")
        self.store.update_settings({"skin": "default"})
        self.assertIsNone(self.store.skin_directory("default"))

    def test_real_antialiased_asset_without_fully_opaque_pixel_is_valid(self):
        skin = self.store.import_skin((ROOT / "assets/sprites/curious.png").read_bytes(), "默认角色副本.png")
        self.assertEqual(skin["kind"], "static")

    def test_skin_rejects_traversal_missing_frames_and_opaque_image(self):
        for filename in ("../curious.png", "skin/code.py", "curious.png"):
            archive = io.BytesIO()
            with ZipFile(archive, "w") as output:
                output.writestr(filename, transparent_png())
            with self.assertRaises(ValueError):
                self.store.import_skin(archive.getvalue(), "bad.zip")
        image = io.BytesIO()
        Image.new("RGB", (100, 150), "yellow").save(image, format="PNG")
        with self.assertRaises(ValueError):
            self.store.import_skin(image.getvalue(), "opaque.png")
        self.assertEqual(len(self.store.skins()), 1)

    def test_support_configuration_is_local_and_rejects_unsafe_links(self):
        self.store.update_support({"name": "测试作者", "message": "谢谢支持", "url": "https://example.com/support"})
        self.store.save_support_image(transparent_png())
        self.assertTrue(self.store.support()["has_image"])
        with self.assertRaises(ValueError):
            self.store.update_support({"name": "测试", "message": "", "url": "javascript:alert(1)"})


class AgentSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "user"
        self.home.mkdir()
        self.store = ControlStore(Path(self.temporary.name) / "state/notifications.sqlite3")
        self.setup = AgentSetup(ROOT, self.store, self.home)

    def test_codex_preview_preserves_other_config_and_backup_and_deduplicates(self):
        directory = self.home / ".codex"
        directory.mkdir()
        original = 'model = "example-model"\n[model_providers.example]\napi_key = "YOUR_API_KEY_HERE"\n'
        path = directory / "config.toml"
        path.write_text(original, encoding="utf-8")
        plan = self.setup.plan("codex", "我的助手")
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertNotIn("YOUR_API_KEY_HERE", json.dumps(plan))
        result = self.setup.apply(plan["plan_id"])
        self.assertEqual(Path(result["agent"]["backups"][0]).read_text(encoding="utf-8"), original)
        updated = path.read_text(encoding="utf-8")
        self.assertTrue(updated.startswith(original.rstrip()))
        self.assertEqual(updated.count("[mcp_servers.nijika-pet]"), 1)
        second = self.setup.plan("codex", "我的助手")
        self.setup.apply(second["plan_id"])
        self.assertEqual(len(self.store.agents()), 1)
        self.assertEqual(path.read_text(encoding="utf-8"), updated)

    def test_preview_conflict_does_not_overwrite_another_editor(self):
        plan = self.setup.plan("codex", "Codex")
        directory = self.home / ".codex"
        directory.mkdir()
        path = directory / "config.toml"
        path.write_text("# changed by another editor\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "其他程序"):
            self.setup.apply(plan["plan_id"])
        self.assertEqual(path.read_text(encoding="utf-8"), "# changed by another editor\n")
        self.assertFalse((directory / "AGENTS.md").exists())

    def test_dsh_both_profiles_preserve_existing_patch_and_repeat_without_duplicate(self):
        for profile in ("desktop", "web"):
            path = self.home / ".dsh/profiles" / profile / "cordis.patch.yml"
            path.parent.mkdir(parents=True)
            path.write_text("# keep existing DSH patch\n", encoding="utf-8")
        for _ in range(2):
            plan = self.setup.plan("dsh", "DSH's 助手")
            self.setup.apply(plan["plan_id"])
        for profile in ("desktop", "web"):
            value = (self.home / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
            self.assertTrue(value.startswith("# keep existing DSH patch"))
            self.assertEqual(value.count("id: mcp-nijika-pet"), 1)
            self.assertIn("DSH''s 助手", value)

    def test_custom_export_never_writes_unknown_client_and_no_arbitrary_command(self):
        plan = self.setup.plan("custom", "自定义助手")
        self.assertFalse(plan["files"])
        self.assertFalse(plan["external_action"])
        self.assertEqual(plan["export"]["mcpServers"]["nijika-pet"]["command"], str(ROOT / "dist/虹夏MCP-v2.exe"))
        result = self.setup.apply(plan["plan_id"])
        self.assertEqual(result["agent"]["status"], "exported")
        self.assertFalse((self.home / ".dsh").exists())

    def test_work_uses_private_staging_and_isolated_cli_home(self):
        with patch("agent_setup.shutil.which", return_value="codex.exe"):
            plan = self.setup.plan("work", "Work 助手")
        with patch("agent_setup.subprocess.run") as run:
            run.return_value.returncode = 0
            result = self.setup.apply(plan["plan_id"])
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["env"]["CODEX_HOME"], str(self.home / ".codex"))
                self.assertNotIn("shell", call.kwargs)
        self.assertEqual(result["agent"]["status"], "configured")
        manifest = self.store.root / "integrations/work/plugins/nijika-work-local/mcp.json"
        content = json.loads(manifest.read_text(encoding="utf-8"))
        server = content["mcpServers"]["nijika-work-pet"]
        self.assertEqual(server["args"][-1], str(self.setup.mcp))
        self.assertEqual(server["env"]["NIJIKA_AGENT_NAME"], "Work 助手")


class LocalAPITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.app = ControlApplication(base / "state/notifications.sqlite3", ROOT, base / "user")
        self.server = ControlServer(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, path, payload=None, token=True, origin=None):
        headers = {"X-Nijika-Token": self.server.token} if token else {}
        if origin:
            headers["Origin"] = origin
        request = Request(self.server.origin + path, json.dumps(payload).encode() if payload is not None else None, headers)
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read())

    def test_no_token_and_foreign_origin_rejected_valid_session_works(self):
        for token, origin in ((False,None), (True,"https://example.com"), (True,"null")):
            with self.assertRaises(HTTPError) as error:
                self.call("/api/state",token=token,origin=origin)
            self.assertEqual(error.exception.code,403)
        self.assertFalse(self.call("/api/state")["renderer"]["online"])
        with urlopen(self.server.origin, timeout=3) as response:
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertNotIn(b"NIJIKA_SESSION_TOKEN",response.read())

    def test_same_pending_test_reused_click_readback_is_not_external_agent_verification(self):
        plan = self.call("/api/agents/plan", {"client":"custom","name":"本机测试"})
        result = self.call("/api/agents/apply", {"plan_id":plan["plan_id"]})
        self.assertEqual(result["agent"]["guide"]["title"], "接下来请照这 5 步做")
        self.assertIn("nijika-pet", result["agent"]["guide"]["prompt"])
        files = result["agent"]["needed_files"]
        self.assertTrue(any(str(ROOT / "dist/虹夏MCP-v2.exe") == item["path"] for item in files))
        self.assertTrue(all("label" in item and "exists" in item for item in files))
        first = self.call("/api/agents/test", {"id":result["agent"]["id"]})
        second = self.call("/api/agents/test", {"id":result["agent"]["id"]})
        self.assertEqual(first["request_id"],second["request_id"])
        self.assertFalse(first["visible"])
        self.app.notifications.answer(first["request_id"],0)
        reply = self.call("/api/notices/" + first["request_id"])
        self.assertEqual(reply["choice"],"收到测试")
        agent = self.call("/api/state")["agents"][0]
        self.assertEqual(agent["guide"]["title"], "接下来请照这 5 步做")
        self.assertEqual(len(agent["guide"]["steps"]), 5)
        self.assertTrue(len(agent["needed_files"]) >= 3)
        self.assertEqual(reply["status"],"answered")
        self.assertEqual(self.call("/api/state")["agents"][0]["status"],"exported")

    def test_focus_reminder_and_note_endpoints_drive_the_companion_snapshot(self):
        started = self.call("/api/focus",{"action":"start"})
        self.assertEqual(started["status"],"running")
        self.assertGreater(started["remaining_seconds"],0)
        configured = self.call("/api/focus",{"action":"configure","focus_minutes":30,"break_minutes":10})
        self.assertEqual((configured["focus_minutes"],configured["break_minutes"]),(30,10))
        with self.assertRaises(HTTPError):
            self.call("/api/focus",{"action":"configure","focus_minutes":999,"break_minutes":10})
        with self.assertRaises(HTTPError):
            self.call("/api/focus",{"action":"explode"})

        reminders = self.call("/api/reminders",{"enabled":True,"sedentary_minutes":70,"water_minutes":30,"eye_minutes":20})
        self.assertEqual(reminders["sedentary_minutes"],70)
        paused = self.call("/api/reminders",{"pause_minutes":30})
        self.assertGreater(paused["paused_until"],time.time())
        with self.assertRaises(HTTPError):
            self.call("/api/reminders",{"water_minutes":3})

        note = self.call("/api/notes",{"action":"add","text":"  写周报  "})
        self.assertEqual(note["text"],"写周报")
        self.assertTrue(self.call("/api/notes",{"action":"toggle","id":note["id"]})["done"])
        with self.assertRaises(HTTPError):
            self.call("/api/notes",{"action":"add","text":""})
        self.assertTrue(self.call("/api/notes",{"action":"remove","id":note["id"]})["removed"])

        snapshot = self.call("/api/state")["companion"]
        self.assertEqual({"pomodoro","reminders","notes","affection"},set(snapshot))
        self.assertEqual(snapshot["notes"],[])
        self.assertGreaterEqual(snapshot["affection"]["points"],1)


if __name__ == "__main__":
    unittest.main()
