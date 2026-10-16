"""Notice-only approval hooks for Codex and Claude Code. Never returns permission decisions."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import PureWindowsPath

from notification_store import NotificationStore


def event_key(event: dict) -> str:
    inputs = event.get("tool_input") or {}
    if event.get("tool_name") in ("Bash", "apply_patch") and isinstance(inputs, dict):
        inputs = inputs.get("command")
    identity = [event.get("session_id"), event.get("turn_id"),
                event.get("tool_name"), inputs]
    # Raw commands and approval inputs are neither stored nor logged.
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def handle_event(event: dict, store: NotificationStore, source: str = "codex") -> str | None:
    name = event.get("hook_event_name")
    if name not in ("PermissionRequest", "PostToolUse"):
        return None
    key = event_key(event)
    if name == "PostToolUse":
        store.resolve_approval(key)
        return None
    if source == "claude-code":
        agent, where = "Claude code", "Claude Code 的权限提示"
    else:
        agent, where = "Codex", "Codex 命令审批卡"
    folder = PureWindowsPath(str(event.get("cwd") or "当前任务")).name
    folder = "".join(c for c in folder if ord(c) >= 32)[:20] or "当前任务"
    notice = store.create(
        agent, "命令需要授权",
        f"{folder}的工具操作需要授权。请在 {where}中处理；此气泡只提醒，不授予权限。",
        ("知道了",), event_key=key, kind="approval",
    )
    return notice.id


def main() -> None:
    arguments = sys.argv[1:]
    source = ("claude-code"
              if "claude-code" in arguments or "--source=claude-code" in arguments
              else "codex")
    try:
        payload = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("hook input too large")
        event = json.loads(payload.decode("utf-8-sig"))
        if not isinstance(event, dict):
            raise ValueError("hook input must be an object")
        handle_event(event, NotificationStore(), source)
    except Exception:
        # Fail open for the notification only; the platform still asks for approval.
        where = "Claude Code 原有权限提示" if source == "claude-code" else "Codex 原有审批卡"
        print(f"虹夏审批提醒未发送；请处理 {where}。", file=sys.stderr)
    # Empty stdout / exit 0 leaves the platform's approval flow unchanged.


if __name__ == "__main__":
    main()
