"""Exercise the official MCP client against the real tool declarations."""

import tempfile
import unittest
from pathlib import Path

from mcp import Client

import mcp_server
from notification_store import NotificationStore


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_choice_width_returns_actionable_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = mcp_server.store
            mcp_server.store = NotificationStore(Path(directory) / "notifications.sqlite3")
            try:
                async with Client(mcp_server.mcp) as client:
                    invalid = await client.call_tool(
                        "request_decision",
                        {"task": "显示方式", "question": "请选择", "options": [
                            {"label": "自动隐藏后重新打开查看", "description": "提醒自动收起，可稍后重新打开查看。"},
                            {"label": "保留到手动关闭", "description": "提醒一直显示，直到你手动关闭。"},
                        ]},
                    )
                    self.assertFalse(invalid.is_error)
                    self.assertEqual(invalid.structured_content["status"], "invalid")
                    self.assertIsNone(invalid.structured_content["request_id"])
                    self.assertIn("20 display columns", invalid.structured_content["instruction"])
                    self.assertIsNone(mcp_server.store.next_pending())
                    too_long = await client.call_tool(
                        "request_decision",
                        {"task": "文案审阅", "question": "文" * 81, "options": [
                            {"label": "接受文案", "description": "采用当前短文案，无需回聊天确认。"},
                            {"label": "需要修改", "description": "暂不定稿，稍后说明修改要求。"},
                        ]},
                    )
                    self.assertEqual(too_long.structured_content["status"], "invalid")
                    self.assertIsNone(mcp_server.store.next_pending())
                    corrected = await client.call_tool(
                        "request_decision",
                        {"task": "显示方式", "question": "请选择", "options": [
                            {"label": "30秒后自动收起", "description": "减少桌面占用，但提醒可能被错过。"},
                            {"label": "保留到手动关闭", "description": "提醒一直显示，直到你手动关闭。"},
                        ]},
                    )
                    self.assertEqual(corrected.structured_content["status"], "pending")
                    self.assertIsNotNone(corrected.structured_content["request_id"])
            finally:
                mcp_server.store = previous

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
                                     ("知道了",))
            finally:
                mcp_server.store = previous


if __name__ == "__main__":
    unittest.main()
