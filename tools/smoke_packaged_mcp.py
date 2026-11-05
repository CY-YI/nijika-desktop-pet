"""Verify the frozen MCP server over a real stdio subprocess."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from notification_store import NotificationStore  # noqa: E402


async def main() -> None:
    executable = (Path(sys.argv[1]) if len(sys.argv) > 1 else
                  ROOT / "dist" / "虹夏MCP-v2" / "虹夏MCP-v2.exe")
    if not executable.is_file():
        raise SystemExit(f"Missing packaged MCP server: {executable}")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notifications.sqlite3"
        environment = os.environ.copy()
        environment["NIJIKA_PET_DB_PATH"] = str(path)
        params = StdioServerParameters(command=str(executable), args=[], env=environment)
        async with Client(params) as client:
            tools = await client.list_tools()
            assert {"show_completion", "request_decision", "get_reply", "wait_for_reply"}.issubset(
                {tool.name for tool in tools.tools}
            )
            created = await client.call_tool(
                "request_decision",
                {"task": "打包验证", "question": "请选择", "options": [
                    {"label": "保持现状", "description": "先不改动，继续核对当前运行效果。", "recommended": True},
                    {"label": "优化提醒", "description": "增加说明，让桌面选择更容易理解。"},
                ]},
            )
            assert not created.is_error and created.structured_content
            request_id = created.structured_content["request_id"]
            store = NotificationStore(path)
            assert store.next_pending().id == request_id
            assert store.get(request_id).choice_recommended == (True, False)
            store.answer(request_id, 1)
            result = await client.call_tool("get_reply", {"request_id": request_id})
            assert result.structured_content["status"] == "answered"
            assert result.structured_content["choice"] == "优化提醒"
    print("Packaged MCP stdio and desktop reply queue: OK")


if __name__ == "__main__":
    asyncio.run(main())
