"""Notice-only lifecycle hooks for Codex and Claude Code.

Codex hooks add a completion fallback for substantive main-thread turns.
Claude Code keeps its existing approval-only behavior.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import PureWindowsPath

from notification_store import NotificationStore
from codex_completion import prompt_class, result_class, tool_flags


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
    if source == "claude-code":
        if name not in ("PermissionRequest", "PostToolUse"):
            return None
    elif name not in ("UserPromptSubmit", "PermissionRequest", "PostToolUse", "Stop"):
        return None

    # Subagents have no root UserPromptSubmit lifecycle in the supported
    # protocol. Be conservative if a future host supplies explicit child IDs.
    if source == "codex" and (event.get("agent_id") or event.get("agent_type")):
        return None

    if name == "UserPromptSubmit":
        try:
            store.begin_codex_turn(
                event.get("session_id"), event.get("turn_id"),
                prompt_class(event.get("prompt")),
            )
        except (ValueError, TypeError):
            pass
        return None

    if name == "Stop":
        try:
            notice = store.create_codex_completion_notice(
                event.get("session_id"), event.get("turn_id"),
                result_class=result_class(event.get("last_assistant_message")),
            )
        except (ValueError, TypeError):
            notice = None
        return notice.id if notice is not None else None

    if source == "codex" and name == "PostToolUse":
        substantive, notice_sent = tool_flags(event.get("tool_name"), event.get("tool_response"))
        try:
            store.record_codex_tool(
                event.get("session_id"), event.get("turn_id"),
                substantive=substantive, notice_sent=notice_sent,
            )
        except (ValueError, TypeError):
            pass

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
    expected_event = None
    for index, argument in enumerate(arguments):
        if argument.startswith("--event="):
            expected_event = argument.partition("=")[2]
        elif argument == "--event" and index + 1 < len(arguments):
            expected_event = arguments[index + 1]
    event_name = expected_event
    try:
        payload = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("hook input too large")
        event = json.loads(payload.decode("utf-8-sig"))
        if not isinstance(event, dict):
            raise ValueError("hook input must be an object")
        event_name = event.get("hook_event_name")
        if expected_event and event_name != expected_event:
            raise ValueError("unexpected hook event")
        handle_event(event, NotificationStore(), source)
    except Exception:
        # Completion fallback is best-effort and must not steer or block a turn.
        # Preserve the existing fixed approval failure text, never the payload.
        if source == "claude-code" or event_name == "PermissionRequest":
            where = "Claude Code 原有权限提示" if source == "claude-code" else "Codex 原有审批卡"
            print(f"虹夏审批提醒未发送；请处理 {where}。", file=sys.stderr)
    finally:
        if source == "codex" and (event_name == "Stop" or expected_event == "Stop"):
            # Stop requires JSON, including no-op and failure paths. No decision,
            # continue or additionalContext fields: the host finishes normally.
            print("{}")


if __name__ == "__main__":
    main()
