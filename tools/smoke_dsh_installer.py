"""Configure an isolated DSH home and keep the Chinese packaged path intact."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
                   "-File", str(ROOT / "integrations/dsh/install.ps1"), "-DshRoot", str(root)]
        for _ in range(2):
            result = subprocess.run(command, capture_output=True, timeout=60)
            assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        expected = str(ROOT / "dist" / "虹夏MCP-v2.exe")
        for profile in ("desktop", "web"):
            text = (root / "profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
            assert expected in text, text
            assert text.count(MARKERS[0]) == 1, text
            assert "magpie-mcp-nijika-pet" not in text, text
            assert sibling in text, text
        assert (root / "skills" / "nijika-dsh-dialog" / "SKILL.md").is_file()
        instructions = (root / "AGENTS.md").read_text(encoding="utf-8")
        assert "wait_for_reply" in instructions and "nijika-dsh-dialog" in instructions
        assert instructions.count(MARKERS[1]) == 1, instructions
    print("DSH installer keeps the Chinese exe path and stays idempotent under "
          "PowerShell 5.1: OK")


if __name__ == "__main__":
    main()
