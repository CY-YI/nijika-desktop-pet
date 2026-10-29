"""Build a private Windows trial ZIP without sender-specific paths or state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from support_bundle import read_bundle
PREFIX = "虹夏桌宠-Windows私下试用"
FILES = (
    "00-解压后先看.txt",
    "dist/虹夏桌宠.exe",
    "dist/虹夏MCP-v2.exe",
    "dist/虹夏审批提醒.exe",
    "integrations/codex/hooks.example.json",
    "integrations/codex/install-hooks.ps1",
    "integrations/claude-code/install-hooks.ps1",
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
    "AGENT_SETUP.md",
    "SKIN_FORMAT.md",
)


def build(output: Path, app_exe: Path | None = None, mcp_exe: Path | None = None,
          support_bundle: Path | None = None) -> None:
    overrides = {"dist/虹夏桌宠.exe": app_exe, "dist/虹夏MCP-v2.exe": mcp_exe}
    sources = {name: overrides.get(name) or ROOT / name for name in FILES}
    missing = [name for name, source in sources.items() if not source.is_file()]
    if missing:
        raise FileNotFoundError("Missing release files: " + ", ".join(missing))
    public = read_bundle(support_bundle.read_bytes()) if support_bundle else {}
    manifest: dict[str, str] = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name in FILES:
            data = sources[name].read_bytes()
            if name == "plugins/nijika-work-local/mcp.json":
                plugin = json.loads(data)
                plugin["mcpServers"]["nijika-work-pet"]["args"][-1] = "AUTO_LOCAL_MCP"
                data = (json.dumps(plugin, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            manifest[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(f"{PREFIX}/{name}", data)
        for name, data in public.items():
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
    parser.add_argument("--app-exe", type=Path,
                        help="Use a reviewed candidate app without replacing the installed/dist executable")
    parser.add_argument("--mcp-exe", type=Path,
                        help="Use the matching candidate MCP server without replacing installed/dist files")
    parser.add_argument("--support-bundle", type=Path,
                        help="Include explicitly exported public sponsor information; never read a user database")
    args = parser.parse_args()
    destination = args.output
    build(destination, args.app_exe, args.mcp_exe, args.support_bundle)
    print(destination)
    print("SHA256:", hashlib.sha256(destination.read_bytes()).hexdigest())
