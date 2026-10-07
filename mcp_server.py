"""Codex-facing MCP tools for the local Nijika desktop pet."""

from __future__ import annotations

import asyncio
import os
import time

from mcp.server import MCPServer
from pydantic import BaseModel, Field

from notification_store import NotificationStore


AGENT_NAME = os.environ.get("NIJIKA_AGENT_NAME", "Codex")
mcp = MCPServer("nijika-desktop-pet")
store = NotificationStore()


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


def invalid_notice(error: ValueError) -> CreatedResult:
    return CreatedResult(
        request_id=None,
        status="invalid",
        instruction=f"Nothing was shown on the desktop: {error}. Shorten or correct the input and retry once.",
    )


@mcp.tool()
def show_completion(task: str, summary: str) -> CreatedResult:
    """Send a notice-only completion alert when the result needs fuller review elsewhere; not an approval request."""
    try:
        notice = store.create(AGENT_NAME, task, summary, ("知道了",))
    except ValueError as error:
        return invalid_notice(error)
    return CreatedResult(
        request_id=notice.id, status=notice.status,
        instruction="Call get_reply or wait_for_reply to read the user's desktop response.",
    )


@mcp.tool()
def request_decision(task: str, question: str, options: list[DecisionOption]) -> CreatedResult:
    """Ask and resolve a simple choice entirely on the desktop; include enough context to decide without opening chat."""
    if not 2 <= len(options) <= 3:
        return invalid_notice(ValueError("request_decision requires 2–3 explained choices"))
    if isinstance(question, str) and (len(question) > 80 or question.count("\n") > 2):
        return invalid_notice(ValueError("decision questions must fit within 80 characters and 3 paragraphs"))
    try:
        notice = store.create(AGENT_NAME, task, question,
                              [option.model_dump() for option in options])
    except ValueError as error:
        return invalid_notice(error)
    return CreatedResult(
        request_id=notice.id, status=notice.status,
        instruction="Call wait_for_reply with this request_id, then continue this task from the selected choice. Pending is not a decision; wait again or use get_reply later.",
    )


@mcp.tool()
def get_reply(request_id: str) -> ReplyResult:
    """Read a desktop request's status and selected choice without waiting."""
    notice = store.get(request_id)
    return ReplyResult(**(notice.result() if notice else
                          {"request_id": request_id, "status": "not_found"}))


@mcp.tool()
async def wait_for_reply(request_id: str, timeout_seconds: int = 20) -> ReplyResult:
    """Wait up to 60 seconds for a desktop click; repeat if the result remains pending."""
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
