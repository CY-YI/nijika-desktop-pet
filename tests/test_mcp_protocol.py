"""Exercise the official MCP client against the real tool declarations."""

import tempfile
import unittest
from pathlib import Path

from mcp import Client

import mcp_server
from notification_store import NotificationStore


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_codex_tool_to_desktop_reply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = mcp_server.store
            mcp_server.store = NotificationStore(Path(directory) / "notifications.sqlite3")
            try:
                async with Client(mcp_server.mcp) as client:
                    tools = await client.list_tools()
                    self.assertIn("request_decision", {tool.name for tool in tools.tools})
                    unexplained = await client.call_tool(
                        "request_decision",
                        {"task": "下一步", "question": "请选择", "options": ["方案A", "方案B"]},
                    )
                    self.assertTrue(unexplained.is_error)
                    created = await client.call_tool(
                        "request_decision",
                        {"task": "下一步", "question": "采用哪个方案？",
                         "options": [
                             {"label": "保留现状", "description": "不改动作，先验证提醒流程。"},
                             {"label": "增强动作", "description": "增加弹跳，让提醒更加醒目。"},
                         ]},
                    )
                    self.assertIsNotNone(created.structured_content, repr(created))
                    request_id = created.structured_content["request_id"]
                    self.assertEqual(mcp_server.store.next_pending().id, request_id)
                    mcp_server.store.answer(request_id, 1)
                    reply = await client.call_tool("get_reply", {"request_id": request_id})
                    self.assertEqual(reply.structured_content["choice"], "增强动作")
                    self.assertIn("弹跳", reply.structured_content["choice_description"])
                    self.assertEqual(reply.structured_content["status"], "answered")
                    completed = await client.call_tool(
                        "show_completion", {"task": "任务完成", "summary": "请查看成果"}
                    )
                    finished_id = completed.structured_content["request_id"]
                    self.assertEqual(mcp_server.store.get(finished_id).choices,
                                     ("已查看", "稍后"))
            finally:
                mcp_server.store = previous


if __name__ == "__main__":
    unittest.main()
