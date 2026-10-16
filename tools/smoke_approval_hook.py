"""Exercise the packaged notice-only hook and its installer in isolation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from approval_hook import event_key  # noqa: E402
from notification_store import NotificationStore  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="nijika-hook-") as directory:
        root = Path(directory)
        # Apostrophes, Unicode and spaces must survive the fixed command quoting.
        executable = root / "space ' 中文" / "虹夏审批提醒.exe"
        executable.parent.mkdir()
        shutil.copy2(ROOT / "dist" / executable.name, executable)
        home = root / "codex"
        home.mkdir()
        unrelated = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo preserved"}]}
        config_path = home / "hooks.json"
        config_path.write_text(json.dumps({"hooks": {"PermissionRequest": [unrelated]}}), encoding="utf-8")
        install = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                   "-File", str(ROOT / "integrations/codex/install-hooks.ps1"),
                   "-CodexHome", str(home), "-ApprovalExe", str(executable)]
        for _ in range(2):
            installed = subprocess.run(install, capture_output=True, timeout=20)
            if installed.returncode:
                raise RuntimeError(installed.stderr.decode("utf-8", errors="replace"))
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        assert config["hooks"]["PermissionRequest"][0] == unrelated
        assert len(config["hooks"]["PermissionRequest"]) == 2
        assert len(config["hooks"]["PostToolUse"]) == 1
        assert len(list(home.glob("hooks.json.bak-nijika-*"))) == 2
        assert set(p.name for p in home.iterdir()) == {
            "hooks.json", *(p.name for p in home.glob("hooks.json.bak-nijika-*"))
        }, "Installer must not create trust or permission state"
        store = NotificationStore(root / "queue.sqlite3")
        environment = os.environ.copy()
        environment["NIJIKA_PET_DB_PATH"] = str(store.path)
        event = {"hook_event_name": "PermissionRequest", "session_id": "smoke-session",
                 "turn_id": "smoke-turn", "tool_name": "Bash", "cwd": "C:/isolated-test",
                 "tool_input": {"command": "TEST_PRIVATE_COMMAND", "description": "reason"}}

        def run_hook(name: str) -> None:
            event["hook_event_name"] = name
            group = config["hooks"][name][-1]
            command = group["hooks"][0]["command"]
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                input=json.dumps(event).encode("utf-8"), capture_output=True,
                env=environment, check=True, timeout=20,
            )
            assert result.stdout == b"", "Hook must not grant or deny permission"
            assert result.stderr == b"", result.stderr

        run_hook("PermissionRequest")
        notice = store.next_pending()
        assert notice is not None and notice.kind == "approval"
        assert "不授予权限" in notice.message
        run_hook("PermissionRequest")
        assert store.next_pending().id == notice.id
        event["tool_input"].pop("description")
        run_hook("PostToolUse")
        assert store.get(notice.id).status == "resolved"
        assert store.get(notice.id).selected_index is None
        assert store.next_pending() is None
        assert b"TEST_PRIVATE_COMMAND" not in store.path.read_bytes()
        assert len(event_key(event)) == 64
        # Claude Code source: exec form with arguments, no turn id, a finished
        # reminder must not swallow the next request, completion auto-resolves.
        cc_event = {"hook_event_name": "PermissionRequest", "session_id": "claude-code-smoke",
                    "tool_name": "Bash", "cwd": "C:/isolated-test",
                    "tool_input": {"command": "TEST_PRIVATE_COMMAND"}}

        def run_cc(name: str) -> None:
            cc_event["hook_event_name"] = name
            result = subprocess.run([str(executable), "--source", "claude-code"],
                                    input=json.dumps(cc_event).encode("utf-8"),
                                    capture_output=True, env=environment, check=True, timeout=20)
            assert result.stdout == b"", "Hook must not grant or deny permission"
            assert result.stderr == b"", result.stderr

        run_cc("PermissionRequest")
        reminder = store.next_pending()
        assert reminder is not None and reminder.agent == "Claude code"
        assert "Claude Code 的权限提示" in reminder.message
        store.answer(reminder.id, 0)
        run_cc("PermissionRequest")
        repeated = store.next_pending()
        assert repeated is not None and repeated.id != reminder.id
        run_cc("PostToolUse")
        assert store.get(repeated.id).status == "resolved"
        assert store.next_pending() is None
    print("Packaged approval hook, safe stdin, installer preservation, deduplication "
          "and Claude Code source: OK")


if __name__ == "__main__":
    main()
