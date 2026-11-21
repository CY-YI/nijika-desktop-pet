import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "Windows DS Bot installer test")
class DsBotInstallerTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_installer(self, dsh_root: Path, mcp_exe: Path, environment: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "powershell",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "integrations/dsbot/install.ps1"),
                "-DsBotRoot",
                str(dsh_root),
                "-McpExe",
                str(mcp_exe),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )

    def test_installs_portable_bundle_and_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="nijika dsbot installer ") as directory:
            base = Path(directory)
            dsh_root = base / "DS Bot Home"
            profile = dsh_root / "profiles/ds-bot"
            profile.mkdir(parents=True)
            profile_package = profile / "package.json"
            profile_package.write_text(
                json.dumps(
                    {
                        "name": "ds-bot-profile",
                        "dependencies": {"unrelated-package": "link:../../unrelated"},
                        "dsh": {"profile": {"bundles": ["unrelated-bundle"]}},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (profile / "pnpm-lock.yaml").write_text(
                "lockfileVersion: '9.0'\n", encoding="utf-8"
            )
            agents = dsh_root / "AGENTS.md"
            agents.write_text("# Existing DS Bot rules\n", encoding="utf-8")

            runtime = base / "MCP runtime with spaces"
            runtime.mkdir()
            mcp_exe = runtime / "nijika-mcp.exe"
            mcp_exe.write_bytes(b"test executable")
            (runtime / "_internal").mkdir()
            (runtime / "_internal/runtime.pyd").write_bytes(b"test runtime")

            target = dsh_root / "integrations/nijika-dsbot-mcp"
            linked = profile / "node_modules/@cy/nijika-dsbot-mcp"
            fake_bin = base / "fake bin"
            fake_bin.mkdir()
            (fake_bin / "pnpm.cmd").write_text(
                "@echo off\r\n"
                f'if exist "{linked}" exit /b 0\r\n'
                f'if not exist "{linked.parent}" mkdir "{linked.parent}"\r\n'
                f'mklink /J "{linked}" "{target}"\r\n'
                "if errorlevel 1 exit /b 1\r\n"
                "exit /b 0\r\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")

            first = self.run_installer(dsh_root, mcp_exe, environment)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            installed = json.loads(profile_package.read_text(encoding="utf-8"))
            self.assertEqual(
                installed["dependencies"]["@cy/nijika-dsbot-mcp"],
                "link:" + target.as_posix(),
            )
            self.assertEqual(
                installed["dependencies"]["unrelated-package"],
                "link:../../unrelated",
            )
            self.assertEqual(
                installed["dsh"]["profile"]["bundles"],
                ["unrelated-bundle", "@cy/nijika-dsbot-mcp"],
            )
            self.assertTrue(linked.exists())

            yaml = (target / "cordis.patch.yml").read_text(encoding="utf-8")
            self.assertNotIn("__NIJIKA_MCP_EXE__", yaml)
            self.assertIn(str(mcp_exe), yaml)
            self.assertNotIn(str(ROOT), yaml)

            skill = (target / "skill/SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(
                skill,
                (ROOT / "integrations/dsbot/nijika-mcp/skill/SKILL.md").read_text(
                    encoding="utf-8"
                ),
            )
            global_rules = (dsh_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(global_rules.startswith("# Existing DS Bot rules\n"))
            self.assertEqual(global_rules.count("# BEGIN NIJIKA-DSBOT-DIALOG"), 1)
            self.assertEqual(global_rules.count("# END NIJIKA-DSBOT-DIALOG"), 1)

            package_bytes = profile_package.read_bytes()
            linked_target = os.readlink(linked) if linked.is_symlink() else str(linked.resolve())
            self.assertEqual(Path(linked_target), target.resolve())

            second = self.run_installer(dsh_root, mcp_exe, environment)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(profile_package.read_bytes(), package_bytes)
            rerun_rules = (dsh_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(rerun_rules.count("# BEGIN NIJIKA-DSBOT-DIALOG"), 1)
            self.assertEqual(rerun_rules.count("# END NIJIKA-DSBOT-DIALOG"), 1)


if __name__ == "__main__":
    unittest.main()
