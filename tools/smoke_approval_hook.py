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
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "虹夏审批提醒.exe"
    if not source.is_file():
        raise SystemExit(f"Missing packaged approval hook: {source}")
    with tempfile.TemporaryDirectory(prefix="nijika-hook-") as directory:
        root = Path(directory)
        # Apostrophes, Unicode and spaces must survive the fixed command quoting.
        executable = root / "space ' 中文" / "虹夏审批提醒.exe"
        executable.parent.mkdir()
        shutil.copy2(source, executable)
        home = root / "codex"
        home.mkdir()
        unrelated = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo preserved"}]}
        config_path = home / "hooks.json"
        mixed = {"matcher": ".*", "hooks": [
            {"type": "command", "command": "OLD/虹夏审批提醒.exe"},
            {"type": "command", "command": "echo mixed-preserved"},
        ]}
        config_path.write_text(json.dumps({"hooks": {
            "PermissionRequest": [unrelated], "PostToolUse": [mixed], "Stop": [unrelated],
        }}), encoding="utf-8")
        original_notify = b'notify = ["existing-computer-use", "turn-ended"]\n'
        (home / "config.toml").write_bytes(original_notify)
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
        assert len(config["hooks"]["PostToolUse"]) == 2
        assert config["hooks"]["PostToolUse"][0]["hooks"] == [mixed["hooks"][1]]
        assert len(config["hooks"]["UserPromptSubmit"]) == 1
        assert len(config["hooks"]["Stop"]) == 2
        assert (home / "config.toml").read_bytes() == original_notify
        assert len(list(home.glob("hooks.json.bak-nijika-*"))) == 2
        assert set(p.name for p in home.iterdir()) == {
            "hooks.json", "config.toml", *(p.name for p in home.glob("hooks.json.bak-nijika-*"))
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
            if name == "Stop":
                assert json.loads(result.stdout) == {}, "Stop must only return no-op JSON"
            else:
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

        event["turn_id"] = "completion-turn"
        event["prompt"] = "检查 TEST_PRIVATE_PROMPT 的功能并修复"
        run_hook("UserPromptSubmit")
        run_hook("PostToolUse")
        event["last_assistant_message"] = "已完成修复。TEST_PRIVATE_RESPONSE"
        run_hook("Stop")
        completion = store.next_pending()
        assert completion is not None and completion.title == "任务完成"
        store.dismiss(completion.id)
        run_hook("Stop")
        assert store.next_pending() is None

        # A one-line question without any tool use still receives a fallback.
        event["turn_id"] = "question-turn"
        event["prompt"] = "你好吗？"
        event["tool_name"] = "Bash"
        event["tool_response"] = None
        run_hook("UserPromptSubmit")
        event["last_assistant_message"] = "我很好，谢谢。"
        run_hook("Stop")
        question_notice = store.next_pending()
        assert question_notice is not None and question_notice.message == "我很好，谢谢。"
        store.dismiss(question_notice.id)

        # A successful direct tool notice suppresses the generic fallback.
        event["turn_id"] = "explicit-notice-turn"
        run_hook("UserPromptSubmit")
        event["tool_name"] = "mcp__nijika-pet__show_completion"
        event["tool_response"] = {"structuredContent": {
            "request_id": "already-sent", "status": "pending",
        }}
        run_hook("PostToolUse")
        run_hook("Stop")
        assert store.next_pending() is None

        # Codex ambient-suggestion generation is internal even though it runs
        # in the user's project directory. Its JSON must never enter a bubble.
        event["turn_id"] = "ambient-suggestions-turn"
        event["prompt"] = "整理本项目的环境建议"
        event["cwd"] = "C:/isolated-project"
        run_hook("UserPromptSubmit")
        event["last_assistant_message"] = json.dumps({
            "projectRoot": "C:/isolated-project",
            "generatedAtMs": 123456,
            "currentSuggestionIds": ["suggestion-1"],
            "suggestions": [{
                "appId": "codex-document-control",
                "title": "Open a document",
                "description": "Continue the document workflow.",
                "prompt": "Continue",
            }],
        })
        run_hook("Stop")
        assert store.next_pending() is None

        # Codex's private helper runs from its versioned bin directory and
        # returns this exact exclusion object. Keep it quiet without treating
        # every JSON reply from a normal user task as internal.
        event["turn_id"] = "private-helper-turn"
        event["prompt"] = "Return the requested helper object."
        event["cwd"] = (
            "C:/Users/example/AppData/Local/OpenAI/Codex/bin/"
            "0ab0e7a8f3779036"
        )
        run_hook("UserPromptSubmit")
        event["last_assistant_message"] = '{"exclude":[]}'
        run_hook("Stop")
        assert store.next_pending() is None

        # A real user asking for JSON still receives a completion notice. The
        # structured reply is summarized instead of truncating raw JSON into
        # the bubble.
        event["turn_id"] = "user-json-turn"
        event["prompt"] = "请只返回一个 JSON 对象，不要调用工具"
        event["cwd"] = "C:/isolated-project"
        run_hook("UserPromptSubmit")
        event["last_assistant_message"] = '{"status":"ok","items":[1,2,3]}'
        run_hook("Stop")
        json_notice = store.next_pending()
        assert json_notice is not None
        assert json_notice.message == "已返回结构化结果，请查看任务。"
        store.dismiss(json_notice.id)
        for path in store.path.parent.glob("queue.sqlite3*"):
            assert b"TEST_PRIVATE_" not in path.read_bytes()

        # Invalid stdin still returns harmless JSON on the installed Stop command.
        stop_command = config["hooks"]["Stop"][-1]["hooks"][0]["command"]
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", stop_command],
            input=b"bad JSON", capture_output=True, env=environment, check=True, timeout=20,
        )
        assert json.loads(result.stdout) == {} and not result.stderr
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
        assert reminder is not None, "Claude Code PermissionRequest did not create a notice"
        assert (reminder.agent, reminder.software) == ("Claude", "Claude Code"), (
            reminder.agent, reminder.software, reminder.title)
        assert "Claude Code 的权限提示" in reminder.message
        store.answer(reminder.id, 0)
        run_cc("PermissionRequest")
        repeated = store.next_pending()
        assert repeated is not None and repeated.id != reminder.id
        run_cc("PostToolUse")
        assert store.get(repeated.id).status == "resolved"
        assert store.next_pending() is None
    print("Packaged approval/completion hook, safe stdin, installer/notify preservation, "
          "durable deduplication and Claude Code source: OK")


if __name__ == "__main__":
    main()
