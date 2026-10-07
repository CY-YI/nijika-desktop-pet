"""Start the local packaged MCP server with inherited stdio streams."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Expected the packaged MCP executable path", file=sys.stderr)
        return 2
    executable = Path(sys.argv[1])
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
