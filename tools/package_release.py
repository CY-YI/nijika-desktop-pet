"""Build a private Windows trial ZIP without sender-specific paths or state."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "虹夏桌宠-Windows私下试用"
FILES = (
    "dist/虹夏桌宠.exe",
    "dist/虹夏MCP-v2.exe",
    "assets/icons/nijika-shortcut.ico",
    "skills/nijika-desktop-dialog/SKILL.md",
    "plugins/nijika-work-local/plugin.json",
    "plugins/nijika-work-local/mcp.json",
    "plugins/nijika-work-local/scripts/run_mcp.py",
    "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md",
    ".agents/plugins/marketplace.json",
    "integrations/dsh/install.ps1",
    "integrations/dsh/global-instructions.txt",
    "integrations/dsh/nijika-dsh-dialog/SKILL.md",
    "distribution/install.ps1",
    "distribution/codex-global-instructions.txt",
    "distribution/README.md",
)


def build(output: Path) -> None:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing release files: " + ", ".join(missing))
    manifest: dict[str, str] = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name in FILES:
            data = (ROOT / name).read_bytes()
            if name == "plugins/nijika-work-local/mcp.json":
                plugin = json.loads(data)
                plugin["mcpServers"]["nijika-work-pet"]["args"][-1] = "INSTALLER_SETS_THIS_PATH"
                data = (json.dumps(plugin, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            manifest[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(f"{PREFIX}/{name}", data)
        archive.writestr(
            f"{PREFIX}/SHA256SUMS.json",
            (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / f"{PREFIX}-{date.today().isoformat()}.zip")
    destination = parser.parse_args().output
    build(destination)
    print(destination)
    print("SHA256:", hashlib.sha256(destination.read_bytes()).hexdigest())
