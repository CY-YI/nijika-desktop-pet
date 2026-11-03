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
MCP_DIRECTORY = "dist/虹夏MCP-v2"
MCP_EXECUTABLE = f"{MCP_DIRECTORY}/虹夏MCP-v2.exe"
FILES = (
    "00-解压后先看.txt",
    "dist/虹夏桌宠.exe",
    MCP_DIRECTORY,
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
    "integrations/dsh/README.md",
    "integrations/dsh/lifecycle-bridge.mjs",
    "integrations/dsh/global-instructions.txt",
    "integrations/dsh/nijika-dsh-dialog/SKILL.md",
    "distribution/install.ps1",
    "distribution/codex-global-instructions.txt",
    "distribution/README.md",
    "AGENT_SETUP.md",
    "NOTIFICATION_PROTOCOL.md",
    "SKIN_FORMAT.md",
)


def _mcp_source(mcp_exe: Path | None) -> Path:
    source = mcp_exe or (ROOT / MCP_DIRECTORY)
    if source.is_dir():
        executable = source / "虹夏MCP-v2.exe"
    elif source.is_file() and source.name.casefold() == "虹夏mcp-v2.exe":
        source, executable = source.parent, source
    else:
        raise FileNotFoundError(f"Missing onedir MCP directory or executable: {source}")
    if not executable.is_file():
        raise FileNotFoundError(f"Missing onedir MCP executable: {executable}")
    return source


def _release_sources(mcp_exe: Path | None = None) -> dict[str, Path]:
    overrides: dict[str, Path | None] = {
        "dist/虹夏桌宠.exe": None,
        "dist/虹夏审批提醒.exe": None,
    }
    if MCP_DIRECTORY in FILES:
        overrides[MCP_DIRECTORY] = _mcp_source(mcp_exe)
    return {name: overrides.get(name) or ROOT / name for name in FILES}


def _collect_entries(sources: dict[str, Path]) -> list[tuple[str, Path]]:
    entries: list[tuple[str, Path]] = []
    missing: list[str] = []
    for name, source in sources.items():
        if source.is_symlink():
            raise ValueError(f"Release source cannot be a symlink: {source}")
        if source.is_dir():
            files = sorted((path for path in source.rglob("*") if path.is_file()),
                           key=lambda path: path.relative_to(source).as_posix())
            if not files:
                missing.append(name)
            for path in files:
                if path.is_symlink():
                    raise ValueError(f"Release source contains a symlink: {path}")
                entries.append((f"{name}/{path.relative_to(source).as_posix()}", path))
        elif source.is_file():
            entries.append((name, source))
        else:
            missing.append(name)
    if missing:
        raise FileNotFoundError("Missing release files: " + ", ".join(missing))
    return entries


def release_file_names(mcp_directory: Path | None = None) -> list[str]:
    """Return the exact allowlisted file set, including the MCP runtime tree."""
    return [name for name, _ in _collect_entries(_release_sources(mcp_directory))]


def build(output: Path, app_exe: Path | None = None, mcp_exe: Path | None = None,
          support_bundle: Path | None = None, approval_exe: Path | None = None) -> None:
    sources = _release_sources(mcp_exe)
    if app_exe:
        sources["dist/虹夏桌宠.exe"] = app_exe
    if approval_exe:
        sources["dist/虹夏审批提醒.exe"] = approval_exe
    entries = _collect_entries(sources)
    public = read_bundle(support_bundle.read_bytes()) if support_bundle else {}
    manifest: dict[str, str] = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in entries:
            data = source.read_bytes()
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


def stage(output: Path, app_exe: Path | None = None, mcp_exe: Path | None = None,
          support_bundle: Path | None = None, approval_exe: Path | None = None) -> None:
    """Create a clean installer source tree from the same explicit allowlist."""
    if output.exists():
        raise FileExistsError(f"Installer staging directory already exists: {output}")
    sources = _release_sources(mcp_exe)
    if app_exe:
        sources["dist/虹夏桌宠.exe"] = app_exe
    if approval_exe:
        sources["dist/虹夏审批提醒.exe"] = approval_exe
    entries = _collect_entries(sources)
    public = read_bundle(support_bundle.read_bytes()) if support_bundle else {}
    manifest: dict[str, str] = {}
    for name, source in entries:
        data = source.read_bytes()
        if name == "plugins/nijika-work-local/mcp.json":
            plugin = json.loads(data)
            plugin["mcpServers"]["nijika-work-pet"]["args"][-1] = "AUTO_LOCAL_MCP"
            data = (json.dumps(plugin, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        manifest[name] = hashlib.sha256(data).hexdigest()
        target = output / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for name, data in public.items():
        manifest[name] = hashlib.sha256(data).hexdigest()
        target = output / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output / "SHA256SUMS.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / f"{PREFIX}-{date.today().isoformat()}.zip")
    parser.add_argument("--app-exe", type=Path,
                        help="Use a reviewed candidate app without replacing the installed/dist executable")
    parser.add_argument("--mcp-exe", type=Path,
                        help="Use the matching candidate MCP server without replacing installed/dist files")
    parser.add_argument("--approval-exe", type=Path,
                        help="Use the matching candidate lifecycle/approval program without mixing old dist files")
    parser.add_argument("--support-bundle", type=Path,
                        help="Include explicitly exported public sponsor information; never read a user database")
    parser.add_argument("--stage", type=Path,
                        help="Create a new clean installer source directory instead of a ZIP")
    args = parser.parse_args()
    if args.stage:
        if args.output != ROOT / f"{PREFIX}-{date.today().isoformat()}.zip":
            parser.error("--stage and --output are mutually exclusive")
        stage(args.stage, args.app_exe, args.mcp_exe, args.support_bundle, args.approval_exe)
        print(args.stage)
        return
    destination = args.output
    build(destination, args.app_exe, args.mcp_exe, args.support_bundle, args.approval_exe)
    print(destination)
    print("SHA256:", hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
