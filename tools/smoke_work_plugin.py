"""Verify the installed Work plugin's stdio launcher and tool discovery."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "plugins" / "nijika-work-local"
sys.path.insert(0, str(ROOT))
from notification_store import NotificationStore  # noqa: E402


async def main() -> None:
    manifest = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["nijika-work-pet"]
    command = server["command"]
    assert command == "python.exe" and shutil.which(command), command
    args = [part.replace("${PLUGIN_ROOT}", str(PLUGIN)) for part in server["args"]]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notifications.sqlite3"
        environment = os.environ.copy()
        environment["NIJIKA_PET_DB_PATH"] = str(path)
        params = StdioServerParameters(command=command, args=args, env=environment)
        async with Client(params) as client:
            listed = await client.list_tools()
            assert {"show_completion", "request_decision", "get_reply", "wait_for_reply"}.issubset(
                {tool.name for tool in listed.tools}
            )
            created = await client.call_tool(
                "show_completion", {"task": "Work 插件验证", "summary": "本机插件已启动 MCP 服务。"}
            )
            assert not created.is_error and created.structured_content
            request_id = created.structured_content["request_id"]
            assert NotificationStore(path).next_pending().id == request_id
    print("Work plugin launcher and MCP tool discovery: OK")


if __name__ == "__main__":
    asyncio.run(main())
