"""Configure an isolated DSH home and keep the Chinese packaged path intact."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
MARKERS = ("# BEGIN NIJIKA-DSH-MCP", "# BEGIN NIJIKA-DSH-DIALOG")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="nijika-dsh-") as directory:
        root = Path(directory) / ".dsh"
        legacy = (
            '- insert:\n'
            '    # magpie\n'
            '    - id: magpie-mcp-nijika-pet\n'
            '      config:\n'
            '        serverName: "nijika-pet"\n'
            '        env:\n'
            '          NIJIKA_AGENT_NAME: "Claude code"\n'
        )
        sibling = "    - id: unrelated-service\n      name: keep-this-service\n      config: {}\n"
        for profile in ("desktop", "web"):
            folder = root / "profiles" / profile
            folder.mkdir(parents=True)
            (folder / "cordis.patch.yml").write_text("# preserved patch\n" + legacy + sibling, encoding="utf-8")
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                   "-File", str(PROJECT / "integrations/dsh/install.ps1"), "-DshRoot", str(root)]
        for _ in range(2):
            result = subprocess.run(command, capture_output=True, timeout=60)
            assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        expected = str(PROJECT / "dist" / "虹夏MCP-v2" / "虹夏MCP-v2.exe")
        snapshots = {}
        for profile in ("desktop", "web"):
            path = root / "profiles" / profile / "cordis.patch.yml"
            text = path.read_text(encoding="utf-8")
            snapshots[profile] = path.read_bytes()
            assert expected in text, text
            assert text.count(MARKERS[0]) == 1, text
            assert "magpie-mcp-nijika-pet" not in text, text
            assert sibling in text, text
            assert text.count("# BEGIN NIJIKA-DSH-LIFECYCLE") == 1
            assert (PROJECT / "integrations/dsh/lifecycle-bridge.mjs").as_uri() in text
            assert str(PROJECT / "dist/虹夏审批提醒.exe") in text
        assert (root / "skills" / "nijika-dsh-dialog" / "SKILL.md").is_file()
        instructions = (root / "AGENTS.md").read_text(encoding="utf-8")
        assert "wait_for_reply" in instructions and "nijika-dsh-dialog" in instructions
        assert instructions.count(MARKERS[1]) == 1, instructions
        # Both profiles must be preflighted before any write, even if only
        # the second profile has damaged or duplicated lifecycle markers.
        broken = root / "profiles/web/cordis.patch.yml"
        for bad in (
            "\n# BEGIN NIJIKA-DSH-LIFECYCLE\n",
            "\n# END NIJIKA-DSH-LIFECYCLE\n",
        ):
            broken.write_bytes(snapshots["web"] + bad.encode())
            before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = subprocess.run(command, capture_output=True, timeout=60)
            assert result.returncode != 0
            assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        broken.write_bytes(snapshots["web"])
        managed = Path(directory) / "managed"
        for profile in ("desktop", "web"):
            path = managed / "profiles" / profile / "cordis.patch.yml"
            path.parent.mkdir(parents=True)
            path.write_text("# owned by manager\n" + legacy + sibling, encoding="utf-8")
        rules = managed / "AGENTS.md"
        rules.write_bytes(b"existing manager/user rules\n")
        only = [*command[:-1], str(managed), "-LifecycleOnly"]
        for _ in range(2):
            result = subprocess.run(only, capture_output=True, timeout=60)
            assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        for profile in ("desktop", "web"):
            text = (managed / "profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
            assert text.startswith("# owned by manager\n" + legacy + sibling.rstrip("\n"))
            assert text.count("id: magpie-mcp-nijika-pet") == 1
            assert "# BEGIN NIJIKA-DSH-MCP" not in text
            assert text.count("id: nijika-lifecycle-bridge") == 1
        assert rules.read_bytes() == b"existing manager/user rules\n"
        assert not (managed / "skills").exists()
    print("DSH installer keeps the Chinese exe path and stays idempotent under "
          "PowerShell 5.1: OK")


if __name__ == "__main__":
    main()
