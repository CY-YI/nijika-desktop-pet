import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.audit_agent_integrations import ROOT


@unittest.skipUnless(os.name == "nt", "Windows installer smoke test")
class PortableInstallTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: bytes = b"") -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def package(self, base: Path) -> Path:
        package = base / "package source"
        shutil.copy2(ROOT / "distribution/install.ps1",
                     self.write(package, "distribution/install.ps1"))
        for relative in (
            "dist/虹夏桌宠.exe",
            "dist/虹夏MCP-v2.exe",
            "dist/虹夏审批提醒.exe",
            "assets/icons/nijika-shortcut.ico",
            "skills/nijika-desktop-dialog/SKILL.md",
            "distribution/codex-global-instructions.txt",
            "integrations/claude-code/install-hooks.ps1",
            "integrations/dsh/install.ps1",
            "integrations/dsh/lifecycle-bridge.mjs",
            "AGENT_SETUP.md",
            "NOTIFICATION_PROTOCOL.md",
        ):
            self.write(package, relative, relative.encode("utf-8"))
        manifest = {
            "mcpServers": {
                "nijika-work-pet": {
                    "command": "python.exe",
                    "args": ["scripts/run_mcp.py", "AUTO_LOCAL_MCP"],
                }
            }
        }
        self.write(package, "plugins/nijika-work-local/mcp.json",
                   (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return package

    def test_custom_install_root_rewrites_work_mcp_path(self):
        with tempfile.TemporaryDirectory(prefix="虹夏 portable test ") as directory:
            base = Path(directory)
            package = self.package(base)
            install = base / "recipient AppData/NijikaDesktopPet/app"
            codex_home = base / "recipient AppData/codex"
            dsh_home = base / "recipient AppData/dsh"

            result = subprocess.run(
                [
                    "powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(package / "distribution/install.ps1"),
                    "-InstallRoot", str(install),
                    "-CodexHome", str(codex_home),
                    "-DshRoot", str(dsh_home),
                    "-NoLaunch", "-NoShortcuts",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = json.loads(
                (install / "plugins/nijika-work-local/mcp.json").read_text(encoding="utf-8"))
            mcp_path = installed["mcpServers"]["nijika-work-pet"]["args"][-1]
            self.assertEqual(Path(mcp_path), install / "dist/虹夏MCP-v2.exe")
            self.assertNotIn(str(package), json.dumps(installed, ensure_ascii=False))

    def test_custom_codex_home_is_exported_to_cli(self):
        with tempfile.TemporaryDirectory(prefix="虹夏 codex home test ") as directory:
            base = Path(directory)
            package = self.package(base)
            install = base / "收件人 AppData/NijikaDesktopPet/app"
            codex_home = base / "收件人 AppData/自定义 Codex Home"
            binary = base / "stub bin"
            binary.mkdir()
            log = base / "codex-calls.txt"
            self.write(binary, "codex.cmd", (
                "@echo off\r\n"
                ">>\"%NIJIKA_TEST_CODEX_LOG%\" echo home=%CODEX_HOME% args=%*\r\n"
                "if \"%1 %2\"==\"mcp get\" exit /b 1\r\n"
                "exit /b 0\r\n"
            ).encode("utf-8"))
            environment = os.environ.copy()
            environment["PATH"] = str(binary) + os.pathsep + environment.get("PATH", "")
            environment["NIJIKA_TEST_CODEX_LOG"] = str(log)

            result = subprocess.run(
                [
                    "powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(package / "distribution/install.ps1"),
                    "-InstallRoot", str(install),
                    "-CodexHome", str(codex_home),
                    "-DshRoot", str(base / "unused dsh"),
                    "-Codex", "-NoLaunch", "-NoShortcuts",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=60,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = log.read_text(encoding="utf-8")
            self.assertIn(f"home={codex_home}", calls)
            self.assertIn("args=mcp add nijika-pet --", calls)
            self.assertIn(str(install / "dist/虹夏MCP-v2.exe"), calls)
            self.assertTrue((codex_home / "skills/nijika-desktop-dialog/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
