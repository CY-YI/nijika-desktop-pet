"""Exercise the official MCP client against the real tool declarations."""

import tempfile
import unittest
import asyncio
import os
from pathlib import Path
from unittest.mock import patch

from mcp import Client
from mcp.types import Implementation

import mcp_server
from notification_store import NotificationStore
from agent_activity import AgentActivity


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_editor_agent_labels_are_per_call_and_replies_remain_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated = NotificationStore(Path(directory) / "notices.sqlite3")
            with patch.object(mcp_server, "store", isolated), \
                    patch.object(mcp_server, "EDITOR_HOST", ""), \
                    patch.object(mcp_server, "AGENT_NAME", "auto"), \
                    patch.object(mcp_server, "HOST_NAME", ""):
                async with Client(mcp_server.mcp, client_info=Implementation(name="dsh-mcp-client", version="test")) as client:
                    ids = []
                    for identity in ("Codex", "Claude Code", "DSH", "CodeBuddy"):
                        result = await client.call_tool("request_decision", {
                            "task": "同一个任务", "question": "先核对哪项？",
                            "agent_name": identity, "software": "VS Code",
                            "options": [{"label": "配置", "description": "先检查当前配置文件。"},
                                        {"label": "来源", "description": "先检查当前气泡来源。"}]})
                        notice = isolated.get(result.structured_content["request_id"])
                        self.assertEqual((notice.agent, notice.software), (identity, "VS Code"))
                        ids.append(notice.id)
                    self.assertEqual(len(set(ids)), 4)
                    for index, request_id in enumerate(reversed(ids)):
                        isolated.answer(request_id, index % 2)
                        reply = await client.call_tool("get_reply", {"request_id": request_id})
                        self.assertEqual(reply.structured_content["choice_index"], index % 2)
                    result = await client.call_tool("show_completion", {"task": "后端验证", "summary": "来源不应被前一次调用覆盖。"})
                    notice = isolated.get(result.structured_content["request_id"])
                    self.assertEqual((notice.agent, notice.software), ("Agent", "DSH"))

    async def test_dsh_rejects_stale_codex_agent_label_but_keeps_real_model(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated = NotificationStore(Path(directory) / "notices.sqlite3")
            with patch.object(mcp_server, "store", isolated), \
                    patch.object(mcp_server, "EDITOR_HOST", ""), \
                    patch.object(mcp_server, "AGENT_NAME", "auto"), \
                    patch.object(mcp_server, "HOST_NAME", ""):
                async with Client(mcp_server.mcp, client_info=Implementation(name="dsh-mcp-client", version="test")) as client:
                    stale = await client.call_tool("show_completion", {
                        "task": "来源修复", "summary": "验证错误来源会被纠正。",
                        "agent_name": "Codex", "software": "DSH",
                    })
                    stale_notice = isolated.get(stale.structured_content["request_id"])
                    self.assertEqual((stale_notice.agent, stale_notice.software), ("Agent", "DSH"))
                    genuine = await client.call_tool("show_completion", {
                        "task": "来源保留", "summary": "验证明确模型来源会保留。",
                        "agent_name": "DeepSeek", "software": "DSH",
                    })
                    genuine_notice = isolated.get(genuine.structured_content["request_id"])
                    self.assertEqual((genuine_notice.agent, genuine_notice.software), ("DeepSeek", "DSH"))

    async def test_profile_activity_is_recorded_only_by_successful_host_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated = NotificationStore(Path(directory) / "notices.sqlite3")
            profile = "f" * 32
            activity = AgentActivity(isolated.path)
            with patch.object(mcp_server, "store", isolated), patch.dict(os.environ, {"NIJIKA_PROFILE_ID": profile}):
                async with Client(mcp_server.mcp, client_info=Implementation(name="gemini-cli", version="test")) as client:
                    await client.list_tools()
                    self.assertFalse(activity.snapshot(profile)["called"])
                    result = await client.call_tool("request_decision", {"task":"宿主验证", "question":"先核对哪项？", "options":[
                        {"label":"配置", "description":"先核对客户端配置位置。"},
                        {"label":"气泡", "description":"先核对桌面消息与回执。"}]})
                    notice_id = result.structured_content["request_id"]
                    self.assertTrue(activity.snapshot(profile)["called"])
                    self.assertFalse(activity.snapshot(profile)["answered"])
                    isolated.answer(notice_id, 1)
                    reply = await client.call_tool("get_reply", {"request_id":notice_id})
                    self.assertEqual(reply.structured_content["choice"], "气泡")
                    self.assertTrue(activity.snapshot(profile)["answered"])
                    with patch("mcp_server.AgentActivity", side_effect=OSError("unavailable")):
                        notice = await client.call_tool("show_completion", {"task":"降级测试","summary":"验证记录失败仍可发送。"})
                        self.assertEqual(notice.structured_content["status"], "pending")

    async def test_known_callers_correct_stale_labels_without_overriding_custom_or_work(self) -> None:
        cases = [
            ("DSH", "codex-mcp-client", "ChatGPT", "Codex"),
            ("Codex", "@deepseek-ai/dsh-mcp-client", "Agent", "DSH"),
            ("DSH", "claude-code", "Claude", "Claude Code"),
            ("Work", "codex-mcp-client", "ChatGPT", "Work"),
            ("My research agent", "codex-mcp-client", "My research agent", "Codex"),
            ("DSH", "codex-mcp-client-extra", "Agent", "DSH"),
            ("DSH", "unknown-client", "Agent", "DSH"),
            ("Claude code", "gemini-cli", "Gemini", "Gemini CLI"),
            ("DSH", "copilot-cli", "Copilot", "Copilot CLI"),
            ("DSH", "workbuddy", "Agent", "WorkBuddy"),
            ("DSH", "workbuddy-ai", "Agent", "WorkBuddy AI"),
            ("DSH", "claude-desktop", "Claude", "Claude Desktop"),
            ("auto", "vscode", "Agent", "VS Code"),
            ("auto", "obsidian", "Agent", "Obsidian"),
            ("auto", "dsh-mcp-client", "Agent", "DSH"),
            ("Agent", "dsh-mcp-client", "Agent", "DSH"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            isolated = NotificationStore(Path(directory) / "notices.sqlite3")
            with patch.object(mcp_server, "store", isolated):
                for configured, caller, expected, software in cases:
                    with self.subTest(configured=configured, caller=caller), patch.object(mcp_server, "AGENT_NAME", configured), patch.object(mcp_server, "HOST_NAME", ""):
                        async with Client(mcp_server.mcp, client_info=Implementation(name=caller, version="test")) as client:
                            tools = await client.list_tools()
                            complete = next(tool for tool in tools.tools if tool.name == "show_completion")
                            self.assertEqual(set(complete.model_dump(by_alias=True)["inputSchema"]["properties"]),
                                             {"task", "summary", "agent_name", "software"})
                            created = await client.call_tool("show_completion", {"task":"来源检查", "summary":"已完成隔离来源检查。"})
                            self.assertEqual(isolated.get(created.structured_content["request_id"]).agent, expected)
                            self.assertEqual(isolated.get(created.structured_content["request_id"]).software, software)
                            decision = await client.call_tool("request_decision", {"task":"来源选择", "question":"先检查哪项？", "options":[
                                {"label":"界面", "description":"先检查当前界面交互结果。"},
                                {"label":"来源", "description":"先检查当前通知来源结果。"}]})
                            self.assertEqual(isolated.get(decision.structured_content["request_id"]).agent, expected)

    async def test_concurrent_clients_keep_their_own_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated = NotificationStore(Path(directory) / "notices.sqlite3")
            with patch.object(mcp_server, "store", isolated), patch.object(mcp_server, "AGENT_NAME", "DSH"), patch.object(mcp_server, "HOST_NAME", ""):
                async with Client(mcp_server.mcp, client_info=Implementation(name="codex-mcp-client", version="test")) as codex:
                    async with Client(mcp_server.mcp, client_info=Implementation(name="@deepseek-ai/dsh-mcp-client", version="test")) as dsh:
                        results = await asyncio.gather(
                            codex.call_tool("show_completion", {"task":"并发检查一", "summary":"第一条隔离检查。"}),
                            dsh.call_tool("show_completion", {"task":"并发检查二", "summary":"第二条隔离检查。"}),
                        )
                        self.assertEqual([isolated.get(result.structured_content["request_id"]).agent for result in results],
                                         ["ChatGPT", "Agent"])

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
                             {"label": "保留现状", "description": "不改动作，先验证提醒流程。", "recommended": True},
                             {"label": "增强动作", "description": "增加弹跳，让提醒更加醒目。"},
                         ]},
                    )
                    self.assertIsNotNone(created.structured_content, repr(created))
                    request_id = created.structured_content["request_id"]
                    self.assertEqual(mcp_server.store.next_pending().id, request_id)
                    self.assertEqual(mcp_server.store.get(request_id).choice_recommended,
                                     (True, False))
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
