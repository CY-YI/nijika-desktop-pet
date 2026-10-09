"""Start the local packaged MCP server with inherited stdio streams."""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


def resolve_executable(argument: str) -> Path:
    if argument != "AUTO_LOCAL_MCP":
        return Path(argument)
    script = Path(__file__).resolve()
    candidates = []
    override = os.environ.get("NIJIKA_MCP_EXE")
    if override:
        candidates.append(Path(override))
    candidates.append(script.parents[3] / "dist" / "虹夏MCP-v2.exe")
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "NijikaDesktopPet" / "app" / "dist" / "虹夏MCP-v2.exe")
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def main() -> int:
    if len(sys.argv) != 2:
        print("Expected the packaged MCP executable path", file=sys.stderr)
        return 2
    executable = resolve_executable(sys.argv[1])
    if not executable.is_file():
        print(f"Missing packaged MCP executable: {executable}", file=sys.stderr)
        return 2
    try:
        return subprocess.run(
            [str(executable)],
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            stderr=sys.stderr.buffer,
            cwd=executable.parent,
            check=False,
        ).returncode
    except OSError as exc:
        print(f"Could not start packaged MCP executable: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
