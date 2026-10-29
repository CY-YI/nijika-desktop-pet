"""Codex-facing MCP tools for the local Nijika desktop pet."""

from __future__ import annotations

import asyncio
import os
import time

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import BaseModel, Field

from notification_store import NotificationStore
from notice_source import resolve_source, NoticeSource


AGENT_NAME = os.environ.get("NIJIKA_AGENT_NAME", "auto")
HOST_NAME = os.environ.get("NIJIKA_HOST_NAME", "")
mcp = MCPServer("nijika-desktop-pet")
store = NotificationStore()


def request_source(context: Context | None, agent_name=None, software=None) -> NoticeSource:
    """Resolve each request independently; never share the previous caller."""
    try:
        params = context.session.client_params
        info = getattr(params, "client_info", None) or getattr(params, "clientInfo", None)
        name = info.name if info else ""
    except (AttributeError, ValueError):
        name = ""
    return resolve_source(AGENT_NAME, HOST_NAME, name, agent_name, software)


class CreatedResult(BaseModel):
    request_id: str | None
    status: str
    instruction: str


class ReplyResult(BaseModel):
    request_id: str
    status: str
    choice: str | None = None
    choice_description: str | None = None
    choice_index: int | None = None


class DecisionOption(BaseModel):
    label: str = Field(max_length=20, description="Meaningful visible choice name, at most 20 display columns (about 10 Chinese characters); avoid bare A/B labels")
    description: str = Field(min_length=6, max_length=48, description="One concise sentence explaining what this choice changes or trades off")
    recommended: bool = Field(default=False, description="Mark at most one option as the recommended choice when there is a concrete reason")


def invalid_notice(error: ValueError) -> CreatedResult:
    return CreatedResult(
        request_id=None,
        status="invalid",
        instruction=f"Nothing was shown on the desktop: {error}. Shorten or correct the input and retry once.",
    )


@mcp.tool()
def show_completion(task: str, summary: str, agent_name: str | None = None,
                    software: str | None = None, context: Context = None) -> CreatedResult:
    """Send completion, not approval. Optional agent_name is your Agent identity; software is your host (Work/Codex/VS Code/Obsidian). Keep task free of source prefixes."""
    try:
        source = request_source(context, agent_name, software)
        notice = store.create(source.agent, task, summary, ("知道了",), software=source.software)
    except ValueError as error:
        return invalid_notice(error)
    return CreatedResult(
        request_id=notice.id, status=notice.status,
        instruction="Call get_reply or wait_for_reply to read the user's desktop response.",
    )


@mcp.tool()
def request_decision(task: str, question: str, options: list[DecisionOption],
                     agent_name: str | None = None, software: str | None = None,
                     context: Context = None) -> CreatedResult:
    """Ask a choice; record the click in chat. Optional agent_name identifies the Agent; software identifies its host. Keep task free of source prefixes."""
    if not 2 <= len(options) <= 3:
        return invalid_notice(ValueError("request_decision requires 2–3 explained choices"))
    if isinstance(question, str) and (len(question) > 80 or question.count("\n") > 2):
        return invalid_notice(ValueError("decision questions must fit within 80 characters and 3 paragraphs"))
    if sum(option.recommended for option in options) > 1:
        return invalid_notice(ValueError("at most one choice may be recommended"))
    try:
        source = request_source(context, agent_name, software)
        notice = store.create(source.agent, task, question,
                              [option.model_dump() for option in options], software=source.software)
    except ValueError as error:
        return invalid_notice(error)
    return CreatedResult(
        request_id=notice.id, status=notice.status,
        instruction="Queued locally, not confirmed visible on screen. Keep this request_id; do not send a duplicate while pending. Call wait_for_reply, then write the selected choice in the Codex chat before continuing. Pending is not a decision.",
    )


@mcp.tool()
def get_reply(request_id: str) -> ReplyResult:
    """Read a desktop reply; when answered, state the selected choice in the Codex chat before continuing."""
    notice = store.get(request_id)
    return ReplyResult(**(notice.result() if notice else
                          {"request_id": request_id, "status": "not_found"}))


@mcp.tool()
async def wait_for_reply(request_id: str, timeout_seconds: int = 20) -> ReplyResult:
    """Wait up to 60 seconds for a click; when answered, state the choice in the Codex chat before continuing."""
    if not 1 <= timeout_seconds <= 60:
        raise ValueError("timeout_seconds must be 1–60")
    deadline = time.monotonic() + timeout_seconds
    while True:
        notice = store.get(request_id)
        if notice is None:
            return ReplyResult(request_id=request_id, status="not_found")
        if notice.status != "pending" or time.monotonic() >= deadline:
            return ReplyResult(**notice.result())
        await asyncio.sleep(0.25)


if __name__ == "__main__":
    mcp.run()
