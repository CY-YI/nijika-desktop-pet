import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import package_release

ROOT = Path(__file__).resolve().parents[1]


class InstallerPackagingTests(unittest.TestCase):
    def test_stage_uses_allowlist_and_recipient_placeholder(self):
        with tempfile.TemporaryDirectory(prefix="nijika installer stage ") as directory:
            base = Path(directory)
            source = base / "source"
            output = base / "stage"
            for name in package_release.FILES:
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(name.encode("utf-8"))
            (source / "plugins/nijika-work-local/mcp.json").write_text(
                json.dumps({"mcpServers": {"nijika-work-pet": {"args": ["AUTO_LOCAL_MCP"]}}}),
                encoding="utf-8")
            (source / "notifications.sqlite3").write_bytes(b"must not ship")
            with patch.object(package_release, "ROOT", source):
                package_release.stage(output)
            files = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
            self.assertEqual(files, {*package_release.FILES, "SHA256SUMS.json"})
            self.assertIn("AUTO_LOCAL_MCP", (output / "plugins/nijika-work-local/mcp.json").read_text())
            self.assertFalse((output / "notifications.sqlite3").exists())
            with self.assertRaises(FileExistsError):
                package_release.stage(output)

    @unittest.skipUnless(os.name == "nt", "PowerShell syntax check")
    def test_build_script_has_valid_powershell_syntax(self):
        script = ROOT / "tools/build_installer.ps1"
        result = subprocess.run([
            "powershell", "-NoLogo", "-NoProfile", "-Command",
            "$errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("
            f"'{script}',[ref]$null,[ref]$errors); "
            "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}",
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(os.name == "nt", "Windows installer safety guards")
class InstallerSmokeSafetyTests(unittest.TestCase):
    def setUp(self):
        from tools import smoke_windows_installer
        self.smoke = smoke_windows_installer

    def test_default_rejection_happens_before_any_installer_or_file_write(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "must-not-be-created"
            with patch.object(self.smoke, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "disposable"):
                    self.smoke.verify(Path("unused.exe"), work)
            run.assert_not_called()
            self.assertFalse(work.exists())

    def test_explicit_flag_still_refuses_existing_production_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "NijikaDesktopPet").mkdir()
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}):
                with self.assertRaisesRegex(RuntimeError, "Existing Nijika installation"):
                    self.smoke.require_disposable_session(True)

    def test_existing_registration_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}), \
                    patch.object(self.smoke.winreg, "OpenKey") as open_key:
                with self.assertRaisesRegex(RuntimeError, "uninstall registration"):
                    self.smoke.require_disposable_session(True)
                open_key.return_value.Close.assert_called_once()

    def test_existing_shortcuts_are_protected_even_with_custom_install_path(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            desktop = base / "Desktop"
            desktop.mkdir()
            shortcut = desktop / "虹夏桌宠.lnk"
            shortcut.write_bytes(b"existing shortcut")
            paths = {0x10: desktop, 0x02: base / "Programs", 0x07: base / "Startup"}
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}), \
                    patch.object(self.smoke.winreg, "OpenKey", side_effect=FileNotFoundError), \
                    patch.object(self.smoke, "known_folder", side_effect=paths.__getitem__):
                with self.assertRaisesRegex(RuntimeError, "Existing Nijika shortcuts"):
                    self.smoke.require_disposable_session(True)
            self.assertEqual(shortcut.read_bytes(), b"existing shortcut")


if __name__ == "__main__":
    unittest.main()
