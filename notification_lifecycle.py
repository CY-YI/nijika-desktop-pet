"""One versioned event contract and policy shared by local host adapters.

This module receives host events; it does not discover turns by polling a chat
log or asking a model to call an extra tool. Payload text stays in memory.
"""
from __future__ import annotations

from notice_source import resolve_source
from notification_policy import completion_preview, prompt_class, result_class, tool_flags
from notification_store import NotificationStore

VERSION = 1
EVENTS = {"turn_started", "tool_finished", "turn_completed"}


def handle_lifecycle(event: dict, store: NotificationStore) -> str | None:
    if not isinstance(event, dict) or type(event.get("version")) is not int or event["version"] != VERSION:
        raise ValueError("unsupported lifecycle protocol version")
    name = event.get("event")
    if name not in EVENTS:
        raise ValueError("unsupported lifecycle event")
    client = event.get("client_id")
    session, turn = event.get("session_id"), event.get("turn_id")
    # No 'most recent turn' inference: adapters must supply all three IDs.
    store._turn_identity(session, turn, client)
    origin = event.get("origin")
    if origin not in {"user", "background", "subagent"}:
        raise ValueError("explicit lifecycle origin is required")
    if origin != "user":
        return None
    if name == "turn_started":
        store.begin_turn(session, turn, prompt_class(event.get("prompt")), client_id=client)
        return None
    if name == "tool_finished":
        substantive, created = tool_flags(event.get("tool_name"), event.get("tool_response"))
        store.record_turn_tool(session, turn, substantive=substantive,
                               notice_sent=created, client_id=client)
        return None
    source = resolve_source("auto", "", client, event.get("agent_name"), event.get("software"))
    message = event.get("last_assistant_message")
    notice = store.create_completion_notice(
        session, turn, client_id=client, agent=source.agent, software=source.software,
        result_class=result_class(message, event.get("cwd"), client_id=client),
        message_preview=completion_preview(message),
    )
    return notice.id if notice else None
