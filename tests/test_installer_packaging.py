import json
import hashlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from support_bundle import read_public_bundle
from tools import package_release

ROOT = Path(__file__).resolve().parents[1]


def png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, format="PNG")
    return output.getvalue()


def materialize_release_source(source: Path) -> None:
    for name in package_release.FILES:
        target = source / name
        if name == package_release.MCP_DIRECTORY:
            (target / "_internal").mkdir(parents=True)
            (target / "虹夏MCP-v2.exe").write_bytes(b"mcp executable")
            (target / "_internal" / "python312.dll").write_bytes(b"mcp runtime")
        elif name in (f"dist/{package_release.PET_RUNTIME_DIRECTORY}",
                      f"dist/{package_release.APPROVAL_RUNTIME_DIRECTORY}"):
            target.mkdir(parents=True)
            for file in ("base_library.zip", "python312.dll"):
                (target / file).write_bytes(b"onedir runtime")
        elif name.endswith("/SKILL.md"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"---\nname: {target.parent.name}\n---\n\n{target.parent.name} fixture\n",
                              encoding="utf-8")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(name.encode("utf-8"))


class InstallerPackagingTests(unittest.TestCase):
    def test_mcp_package_rejects_missing_and_empty_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "虹夏MCP-v2.exe"
            executable.write_bytes(b"exe")
            with self.assertRaisesRegex(FileNotFoundError, "runtime"):
                package_release._mcp_source(executable)
            runtime = root / "_internal"
            runtime.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "runtime"):
                package_release._mcp_source(executable)
            (runtime / "runtime.pyd").write_bytes(b"runtime")
            self.assertEqual(package_release._mcp_source(executable), root)

    def test_friend_guide_uses_actual_version_and_describes_capability_limits(self):
        from tools.package_friend_trial import build
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup, manifest, guide = root / "custom-setup.exe", root / "manifest.json", root / "AGENT_SETUP.md"
            friend_guide = root / "FRIEND_TRIAL_GUIDE.md"
            setup.write_bytes(b"isolated installer fixture")
            manifest.write_text(json.dumps({"version": "9.8.7", "sha256":
                hashlib.sha256(setup.read_bytes()).hexdigest()}), encoding="utf-8")
            guide.write_text("current guide", encoding="utf-8")
            friend_guide.write_text("friend quick guide", encoding="utf-8")
            output = root / "trial.zip"
            build(output, setup, manifest, guide, friend_guide)
            with ZipFile(output) as archive:
                self.assertEqual(len(archive.namelist()), 5)
                self.assertTrue(all(name.startswith("虹夏桌宠-v9.8.7-") for name in archive.namelist()))
                text = archive.read("虹夏桌宠-v9.8.7-朋友私下试用/朋友试用说明.txt").decode("utf-8")
                self.assertIn("custom-setup.exe", text)
                self.assertIn("仅主动调用", text)
                self.assertNotIn("0.1.7", text)
                self.assertEqual(
                    archive.read("虹夏桌宠-v9.8.7-朋友私下试用/FRIEND_TRIAL_GUIDE.md"),
                    b"friend quick guide",
                )

    def test_stage_uses_allowlist_and_recipient_placeholder(self):
        with tempfile.TemporaryDirectory(prefix="nijika installer stage ") as directory:
            base = Path(directory)
            source = base / "source"
            output = base / "stage"
            materialize_release_source(source)
            (source / "plugins/nijika-work-local/mcp.json").write_text(
                json.dumps({"mcpServers": {"nijika-work-pet": {"args": ["AUTO_LOCAL_MCP"]}}}),
                encoding="utf-8")
            (source / "notifications.sqlite3").write_bytes(b"must not ship")
            with patch.object(package_release, "ROOT", source):
                package_release.stage(output)
                files = {path.relative_to(output).as_posix()
                         for path in output.rglob("*") if path.is_file()}
                self.assertEqual(files, {*package_release.release_file_names(), "SHA256SUMS.json"})
            self.assertIn("AUTO_LOCAL_MCP", (output / "plugins/nijika-work-local/mcp.json").read_text())
            self.assertFalse((output / "notifications.sqlite3").exists())
            with self.assertRaises(FileExistsError):
                package_release.stage(output)

    def test_stage_automatically_includes_reviewed_public_support(self):
        with tempfile.TemporaryDirectory(prefix="nijika public support ") as directory:
            base = Path(directory)
            source = base / "source"
            output = base / "stage"
            materialize_release_source(source)
            (source / "plugins/nijika-work-local/mcp.json").write_text(
                json.dumps({"mcpServers": {"nijika-work-pet": {"args": ["AUTO_LOCAL_MCP"]}}}),
                encoding="utf-8")
            public = source / "distribution"
            public.mkdir(exist_ok=True)
            image = png()
            (public / "support.png").write_bytes(image)
            (public / "support.json").write_text(json.dumps({
                "name": "Public author", "message": "Voluntary support",
                "url": "https://example.com/sponsor",
                "image_sha256": hashlib.sha256(image).hexdigest(),
            }), encoding="utf-8")
            with patch.object(package_release, "ROOT", source):
                package_release.stage(output)
            public_files = read_public_bundle(source)
            self.assertEqual((output / "distribution/support.json").read_bytes(),
                             public_files["distribution/support.json"])
            self.assertEqual((output / "distribution/support.png").read_bytes(),
                             public_files["distribution/support.png"])
            self.assertFalse((output / "notifications.sqlite3").exists())

    def test_candidate_package_keeps_all_three_reviewed_executables(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            materialize_release_source(source)
            for path in source.rglob("*"):
                if path.is_file() and path.name != "SKILL.md" and "mcp" not in path.relative_to(source).as_posix().casefold():
                    path.write_bytes(b"old packaged fixture")
            (source / "plugins/nijika-work-local/mcp.json").write_text(
                json.dumps({"mcpServers": {"nijika-work-pet": {"args": ["AUTO_LOCAL_MCP"]}}}),
                encoding="utf-8")
            candidates = [base / "app.exe", base / "mcp" / "虹夏MCP-v2.exe", base / "hook.exe"]
            (base / "mcp" / "_internal").mkdir(parents=True)
            (base / "mcp" / "_internal" / "runtime.pyd").write_bytes(b"reviewed runtime")
            for index, candidate in enumerate(candidates):
                candidate.write_bytes(f"reviewed candidate {index}".encode())
            for name in (package_release.PET_RUNTIME_DIRECTORY, package_release.APPROVAL_RUNTIME_DIRECTORY):
                runtime = base / name
                runtime.mkdir()
                for filename in ("base_library.zip", "python312.dll"):
                    (runtime / filename).write_bytes(f"{name}/{filename}".encode())
            with patch.object(package_release, "ROOT", source):
                package_release.stage(base / "stage", *candidates[:2], approval_exe=candidates[2])
                package_release.build(base / "trial.zip", *candidates[:2], approval_exe=candidates[2])
            skill = base / "stage/plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md"
            self.assertIn("name: nijika-work-dialog", skill.read_text(encoding="utf-8"))
            self.assertIn("nijika-agent-dialog fixture", skill.read_text(encoding="utf-8"))
            self.assertFalse((base / "stage/skills/nijika-desktop-dialog").exists())
            self.assertFalse((base / "stage/integrations/dsbot/install.ps1").exists())
            with ZipFile(base / "trial.zip") as archive:
                sums = json.loads(archive.read(f"{package_release.PREFIX}/SHA256SUMS.json"))
                for name, candidate in (
                    ("dist/虹夏桌宠.exe", candidates[0]),
                    (package_release.MCP_EXECUTABLE, candidates[1]),
                    ("dist/虹夏审批提醒.exe", candidates[2]),
                ):
                    data = candidate.read_bytes()
                    self.assertEqual((base / "stage" / name).read_bytes(), data)
                    self.assertEqual(archive.read(f"{package_release.PREFIX}/{name}"), data)
                    self.assertEqual(sums[name], hashlib.sha256(data).hexdigest())
                runtime = base / "mcp/_internal/runtime.pyd"
                relative = package_release.MCP_DIRECTORY + "/_internal/runtime.pyd"
                self.assertEqual((base / "stage" / relative).read_bytes(), runtime.read_bytes())
                self.assertEqual(archive.read(f"{package_release.PREFIX}/{relative}"), runtime.read_bytes())
                for name in (package_release.PET_RUNTIME_DIRECTORY, package_release.APPROVAL_RUNTIME_DIRECTORY):
                    runtime = f"{name}/python312.dll"
                    self.assertEqual(archive.read(f"{package_release.PREFIX}/dist/{runtime}"), runtime.encode())
                    self.assertEqual((base / "stage" / "dist" / runtime).read_bytes(), runtime.encode())

    def test_missing_approval_runtime_blocks_staging_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            materialize_release_source(source)
            exe = base / "other" / "hook.exe"
            exe.parent.mkdir()
            exe.write_bytes(b"exe without its runtime")
            stage = base / "stage"
            with patch.object(package_release, "ROOT", source):
                with self.assertRaisesRegex(FileNotFoundError, "_nijika_hook_runtime"):
                    package_release.stage(stage, approval_exe=exe)
            self.assertFalse(stage.exists())

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

    def test_upgrade_guard_rejects_two_copies_of_same_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / "previous.exe"
            candidate = root / "candidate.exe"
            for path in (previous, candidate):
                path.write_bytes(b"same installer bytes")
            with patch.object(self.smoke, "require_disposable_session"), patch.object(self.smoke, "run") as run:
                with self.assertRaisesRegex(ValueError, "two distinct Setup binaries"):
                    self.smoke.verify(candidate, root / "empty", disposable_session=True, upgrade_from=previous)
            run.assert_not_called()
            self.assertFalse((root / "empty").exists())

    def test_existing_default_user_data_blocks_even_before_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / ".nijika-desktop-pet"
            existing.mkdir()
            candidate = root / "candidate.exe"
            candidate.touch()
            with patch.object(self.smoke, "require_disposable_session"), \
                    patch.object(self.smoke.Path, "home", return_value=root), patch.object(self.smoke, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "Existing Nijika user data"):
                    self.smoke.verify(candidate, root / "empty", disposable_session=True)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
