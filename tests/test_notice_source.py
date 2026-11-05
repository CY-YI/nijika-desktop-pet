import tempfile
import unittest
from pathlib import Path

from notice_source import resolve_source, notification_source, task_heading
from notification_store import NotificationStore


class NoticeSourceTests(unittest.TestCase):
    def test_explicit_host_distinguishes_shared_engine(self):
        for host in ("Work", "Codex", "VS Code", "Obsidian"):
            source = resolve_source("ChatGPT", host, "codex-mcp-client")
            self.assertEqual(source.heading, f"{host} · ChatGPT" if host == "VS Code" else f"ChatGPT · {host}")
        self.assertEqual(resolve_source("auto", "", "unknown").heading, "Agent · 未识别软件")
        self.assertEqual(resolve_source("auto", "", "dsh", "Claude").heading, "Claude · DSH")
        self.assertEqual(resolve_source("DSH", "", "codex", "Claude", "VS Code").heading, "VS Code · Claude")

    def test_actual_dsh_handshake_from_shared_auto_config(self):
        for configured in ("auto", "Agent", "Claude code"):
            self.assertEqual(resolve_source(configured, "", "dsh-mcp-client").heading,
                             "Agent · DSH")
        self.assertEqual(resolve_source("auto", "", "dsh-mcp-client", "Claude").heading,
                         "Claude · DSH")
        self.assertEqual(resolve_source("auto", "", "dsh-mcp-client-extra").heading,
                         "Agent · 未识别软件")
        self.assertEqual(resolve_source("ChatGPT", "Obsidian", "dsh-mcp-client").heading,
                         "ChatGPT · Obsidian")

    def test_multimodel_host_never_uses_host_product_as_agent_name(self):
        for caller, software, agent_name in (
            ("dsh-mcp-client", "", "Codex"),
            ("dsh-mcp-client", "DSH", "Codex"),
            ("dsh-mcp-client", "DSH", "DSH"),
            ("workbuddy", "WorkBuddy", "Work"),
            ("workbuddy", "WorkBuddy AI", "ChatGPT"),
        ):
            with self.subTest(caller=caller, software=software, agent_name=agent_name):
                self.assertEqual(
                    resolve_source("auto", "", caller, agent_name, software).agent,
                    "Agent",
                )
        self.assertEqual(
            resolve_source("auto", "", "dsh-mcp-client", "DeepSeek", "DSH").heading,
            "DeepSeek · DSH",
        )
        self.assertEqual(
            resolve_source("auto", "", "dsh-mcp-client", "研究助手", "DSH").heading,
            "研究助手 · DSH",
        )
        self.assertEqual(
            resolve_source("auto", "", "vscode", "Codex", "VS Code").heading,
            "VS Code · Codex",
        )

    def test_task_prefixes_removed_only_at_delimited_start(self):
        source = notification_source("ChatGPT", "Codex")
        for task in ("Codex · Codex: 修复问题", "ChatGPT · Codex：修复问题"):
            self.assertEqual(task_heading(task, source), "修复问题")
        for task in ("比较 Codex 和 DSH", "Codex 配置修复", "DSH · 检查"):
            self.assertEqual(task_heading(task, source), task)
        self.assertEqual(notification_source("Claude code").heading, "Claude · Claude Code")

    def test_new_and_old_database_rows_coexist(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "test.sqlite3")
            first = store.create("ChatGPT", "任务", "内容", ["知道了"], software="Obsidian")
            old = store.create("Codex", "旧任务", "内容", ["知道了"])
            with store._connect() as connection:
                connection.execute("DELETE FROM notice_sources WHERE notification_id=?", (old.id,))
                # The old schema is still usable by a previously running MCP.
                connection.execute("INSERT INTO notifications VALUES ('legacy', 'DSH', '任务', '内容', '[\"OK\"]', 'pending', NULL, 1, 1)")
            self.assertEqual(store.get(first.id).software, "Obsidian")
            self.assertEqual(store.get(old.id).software, "")
            self.assertEqual(store.next_pending().id, "legacy")
            self.assertEqual(notification_source(store.get("legacy").agent).heading, "Agent · DSH")
            self.assertEqual(store.answer(first.id, 0).software, "Obsidian")

    def test_source_validation_and_bubble_layout(self):
        from pet import BubbleNotice, render_bubble
        with self.assertRaises(ValueError):
            resolve_source("ChatGPT", "Work\nForged")
        for heading in ("ChatGPT · Work", "ChatGPT · Codex", "Claude · VS Code", "Agent · WorkBuddy AI"):
            notice = BubbleNotice("修复设置界面", "任务已完成，等待查看。", actions=("知道了",),
                                  kind="agent", request_id="isolated", source=heading)
            image, buttons, close = render_bubble(notice)
            self.assertTrue(buttons)
            self.assertGreater(buttons[0][1], 96)
            self.assertLess(buttons[0][3], image.height)
