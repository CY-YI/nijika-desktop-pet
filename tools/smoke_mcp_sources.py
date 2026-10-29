"""Verify caller labels and reply routing over a real, isolated stdio server."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import Implementation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from notification_store import NotificationStore


async def verify(executable: Path) -> None:
    executable = executable.resolve(strict=True)
    cases = (
        ("DSH", "codex-mcp-client", "ChatGPT", "Codex", "auto"),
        ("DSH", "codex-mcp-client", "ChatGPT", "Codex", "legacy"),
        ("Codex", "@deepseek-ai/dsh-mcp-client", "Agent", "DSH", "auto"),
        ("DSH", "claude-code", "Claude", "Claude Code", "auto"),
        ("Work", "codex-mcp-client", "ChatGPT", "Work", "auto"),
        ("My helper", "codex-mcp-client", "My helper", "Codex", "auto"),
        ("DSH", "unknown-client", "Agent", "DSH", "auto"),
        ("DSH", "gemini-cli", "Gemini", "Gemini CLI", "auto"),
        ("Claude code", "copilot-cli", "Copilot", "Copilot CLI", "auto"),
        ("DSH", "workbuddy", "Agent", "WorkBuddy", "auto"),
        ("DSH", "workbuddy-ai", "Agent", "WorkBuddy AI", "auto"),
        ("DSH", "claude-desktop", "Claude", "Claude Desktop", "auto"),
        ("auto", "vscode", "Agent", "VS Code", "auto"),
        ("auto", "obsidian", "Agent", "Obsidian", "auto"),
        ("auto", "dsh-mcp-client", "Agent", "DSH", "auto"),
        ("Agent", "dsh-mcp-client", "Agent", "DSH", "legacy"),
    )
    with tempfile.TemporaryDirectory(prefix="nijika-source-smoke-") as directory:
        for index, (configured, caller, expected, software, mode) in enumerate(cases):
            database = Path(directory) / f"case-{index}.sqlite3"
            params = StdioServerParameters(command=str(executable), args=[], env=dict(
                os.environ, NIJIKA_PET_DB_PATH=str(database), NIJIKA_AGENT_NAME=configured, NIJIKA_HOST_NAME="",
            ))
            store = NotificationStore(database)
            async with Client(params, client_info=Implementation(name=caller, version="source-check"), mode=mode) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "show_completion", "request_decision", "get_reply", "wait_for_reply",
                }
                completed = await client.call_tool("show_completion", {
                    "task": "source-check", "summary": "Isolated completion test.",
                })
                assert not completed.is_error, completed
                assert store.get(completed.structured_content["request_id"]).agent == expected
                assert store.get(completed.structured_content["request_id"]).software == software
                decision = await client.call_tool("request_decision", {
                    "task": "source-choice", "question": "Which check?", "options": [
                        {"label": "Source", "description": "Check the caller source.", "recommended": True},
                        {"label": "Preview", "description": "Check the preview display."},
                    ],
                })
                assert not decision.is_error, decision
                request_id = decision.structured_content["request_id"]
                assert store.get(request_id).agent == expected
                store.answer(request_id, 0)
                reply = await client.call_tool("get_reply", {"request_id": request_id})
                assert reply.structured_content["status"] == "answered"
                assert reply.structured_content["choice"] == "Source"
                # Same engine embedded in another application: explicit
                # per-call identity must survive a frozen round trip.
                detailed = await client.call_tool("show_completion", {
                    "task": "editor-check", "summary": "Isolated host check.",
                    "agent_name": "ChatGPT", "software": "Obsidian"})
                notice = store.get(detailed.structured_content["request_id"])
                assert (notice.agent, notice.software) == ("ChatGPT", "Obsidian")
            print(f"Source {expected}, {mode}: completion, decision and reply OK")
        database = Path(directory) / "shared.sqlite3"
        store = NotificationStore(database)
        async def call_agent(caller: str, expected: str, index: int):
            params = StdioServerParameters(command=str(executable), args=[], env=dict(
                os.environ, NIJIKA_PET_DB_PATH=str(database), NIJIKA_AGENT_NAME="DSH", NIJIKA_HOST_NAME=""))
            async with Client(params, client_info=Implementation(name=caller, version="concurrent-check")) as client:
                result = await client.call_tool("request_decision", {
                    "task": "same-task", "question": "Which check?", "options": [
                        {"label": "Source", "description": "Check the caller source."},
                        {"label": "Preview", "description": "Check the preview display."}]})
                request_id = result.structured_content["request_id"]
                assert store.get(request_id).agent == expected
                store.answer(request_id, index % 2)
                reply = await client.call_tool("wait_for_reply", {"request_id": request_id, "timeout_seconds": 1})
                assert reply.structured_content["status"] == "answered"
                assert reply.structured_content["choice"] == ("Preview" if index % 2 else "Source")
                return request_id
        ids = await asyncio.gather(*(call_agent(caller, expected, index) for index, (caller, expected) in enumerate((
            ("codex-mcp-client", "ChatGPT"), ("@deepseek-ai/dsh-mcp-client", "Agent"),
            ("claude-code", "Claude"), ("codex-mcp-client", "ChatGPT")))))
        assert len(set(ids)) == 4
        print("Concurrent shared database: four stdio clients, same question, independent replies OK")
    print(f"Frozen MCP source checks: {len(cases)} source cases, explicit editor metadata and 4 concurrent clients passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    asyncio.run(verify(parser.parse_args().executable))
