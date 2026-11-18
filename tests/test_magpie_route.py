import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app_layout import bundled_mcp_path
from magpie_route import MagpieDirectRoute


class MagpieDirectRouteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.user = self.base / "user"
        self.root = self.base / "app"
        self.user.mkdir()
        self.mcp = bundled_mcp_path(self.root)
        self.mcp.parent.joinpath("_internal").mkdir(parents=True)
        self.mcp.write_bytes(b"mcp")
        self.cli = self.base / "magpie.exe"
        self.cli.write_bytes(b"test cli")
        self.library = self.user / ".config/magpie/library.json"
        self.library.parent.mkdir(parents=True)
        self.document = {"mcpHub": True, "mcp": [
            {"name": "nijika-pet", "command": str(self.mcp), "args": [],
             "env": {"NIJIKA_AGENT_NAME": "auto"}, "agents": ["codex", "dsh"]},
            {"name": "unrelated", "command": "keep", "agents": ["codex"]},
        ]}
        self.save()
        self.calls = []
        self.environment = patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.user / ".config")})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def save(self):
        self.library.write_text(json.dumps(self.document), encoding="utf-8")

    def run_cli(self, command, **kwargs):
        self.calls.append(command)
        if command[1:] == ["library", "help"]:
            return SimpleNamespace(returncode=0, stdout=b"mcp router <name> shared|direct")
        self.assertEqual(command[1:], ["library", "mcp", "router", "nijika-pet", "direct"])
        self.document["mcp"][0]["hub"] = "direct"
        self.save()
        return SimpleNamespace(returncode=0, stdout=b"")

    def router(self, *, enabled=True, run=None):
        return MagpieDirectRoute(self.user, self.root, use_environment=enabled,
                                 locate=lambda: self.cli, run=run or self.run_cli)

    def test_preview_and_one_shot_apply_touch_only_the_requested_service(self):
        router = self.router()
        before = self.library.read_bytes()
        plan = router.preview("codex")
        self.assertTrue(plan["can_apply"])
        self.assertEqual(plan["targets"], ["codex", "dsh"])
        self.assertEqual(self.library.read_bytes(), before)
        result = router.apply(plan["plan_id"])
        self.assertEqual(result["route"], "direct")
        data = json.loads(self.library.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp"][0]["hub"], "direct")
        self.assertEqual(data["mcp"][1], self.document["mcp"][1])
        with self.assertRaisesRegex(ValueError, "预览已过期"):
            router.apply(plan["plan_id"])

    def test_isolated_preview_cannot_start_or_modify_real_magpie(self):
        router = self.router(enabled=False)
        plan = router.preview("codex")
        self.assertFalse(plan["can_apply"])
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(ValueError, "隔离测试"):
            router.apply("anything")

    def test_changed_library_or_binary_aborts_before_running_switch(self):
        router = self.router()
        plan = router.preview("codex")
        self.document["mcp"][1]["command"] = "changed by someone else"
        self.save()
        with self.assertRaisesRegex(ValueError, "预览后发生变化"):
            router.apply(plan["plan_id"])
        self.assertEqual(len(self.calls), 1)
        plan = router.preview("codex")
        self.cli.write_bytes(b"different binary")
        with self.assertRaisesRegex(ValueError, "程序在预览后发生变化"):
            router.apply(plan["plan_id"])
        self.assertEqual(len(self.calls), 2)

    def test_fixed_identity_or_unknown_runtime_is_not_rewritten(self):
        for change in ({"env": {"NIJIKA_HOST_NAME": "DSH"}},
                       {"env": {"nijika_host_name": "DSH"}}, {"transport": "http"},
                       {"env": {"NIJIKA_PROFILE_ID": "other-profile"}},
                       {"args": ["--unexpected"]}, {"command": str(self.base / "虹夏MCP-v2.exe")}):
            with self.subTest(change=change):
                original = dict(self.document["mcp"][0])
                self.document["mcp"][0].update(change)
                self.save()
                with self.assertRaises(ValueError):
                    self.router().preview("codex")
                self.assertEqual(self.calls, [])
                self.document["mcp"][0] = original

    def test_timeout_is_not_automatically_retried_or_claimed_as_success(self):
        def timeout(command, **kwargs):
            if command[1:] == ["library", "help"]:
                return SimpleNamespace(returncode=0, stdout=b"shared|direct")
            raise subprocess.TimeoutExpired(command, 45)
        router = self.router(run=timeout)
        plan = router.preview("codex")
        with self.assertRaisesRegex(ValueError, "可能已部分同步"):
            router.apply(plan["plan_id"])
        with self.assertRaisesRegex(ValueError, "预览已过期"):
            router.apply(plan["plan_id"])

    def test_lost_runtime_or_disabled_global_router_is_not_reported_as_success(self):
        router = self.router()
        plan = router.preview("codex")
        self.mcp.unlink()
        with self.assertRaisesRegex(ValueError, "安装不完整"):
            router.apply(plan["plan_id"])
        self.assertEqual(len(self.calls), 1)
        self.mcp.write_bytes(b"mcp")

        def global_changed(command, **kwargs):
            if command[1:] == ["library", "help"]:
                return SimpleNamespace(returncode=0, stdout=b"shared|direct")
            self.document["mcpHub"] = False
            self.save()
            return SimpleNamespace(returncode=0, stdout=b"")
        router = self.router(run=global_changed)
        plan = router.preview("codex")
        with self.assertRaisesRegex(ValueError, "未确认完成"):
            router.apply(plan["plan_id"])


if __name__ == "__main__":
    unittest.main()
