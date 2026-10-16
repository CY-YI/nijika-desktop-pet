"""Merge, replace, back up and stay idempotent when installing Claude Code hooks."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "integrations" / "claude-code" / "install-hooks.ps1"


def install(settings: Path, exe: Path) -> None:
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-File", str(SCRIPT), "-UserSettings", str(settings), "-ApprovalExe", str(exe)]
    result = subprocess.run(command, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="nijika-cc-hooks-") as directory:
        root = Path(directory)
        exe = ROOT / "dist" / "虹夏审批提醒.exe"
        home = root / ".claude"
        home.mkdir()
        settings = home / "settings.json"
        legacy = {"matcher": ".*", "hooks": [{
            "type": "command", "command": r"C:\x\.venv\Scripts\python.exe",
            "args": [r"C:\x\approval_hook.py", "--source", "claude-code"], "timeout": 10}]}
        unrelated = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo preserved"}]}
        settings.write_text(json.dumps(
            {"promptCacheTtl": "1h",
             "hooks": {"PermissionRequest": [unrelated, legacy], "Stop": [unrelated]}},
            ensure_ascii=False), encoding="utf-8")
        for _ in range(2):
            install(settings, exe)
        config = json.loads(settings.read_text(encoding="utf-8-sig"))
        assert config["promptCacheTtl"] == "1h"
        assert config["hooks"]["Stop"] == [unrelated]
        permission = config["hooks"]["PermissionRequest"]
        assert permission[0] == unrelated and len(permission) == 2, permission
        entry = permission[-1]
        assert str(exe) == entry["hooks"][0]["command"]
        assert entry["hooks"][0]["args"] == ["--source", "claude-code"]
        assert entry["hooks"][0]["type"] == "command"
        post = config["hooks"]["PostToolUse"]
        assert len(post) == 1 and post[0]["hooks"][0]["async"] is True
        backups = list((home / "backups").glob("settings.json.backup.nijika-*"))
        assert len(backups) == 2, backups
        # Fresh machine: no .claude home or settings file exists yet.
        fresh = root / "fresh" / ".claude" / "settings.json"
        install(fresh, exe)
        created = json.loads(fresh.read_text(encoding="utf-8"))
        assert set(created["hooks"]) == {"PermissionRequest", "PostToolUse"}
        assert len(created["hooks"]["PostToolUse"]) == 1
        assert not list(fresh.parent.glob("backups"))
    print("Claude Code hook installer merge, replacement, backup, idempotency "
          "and fresh install: OK")


if __name__ == "__main__":
    main()
