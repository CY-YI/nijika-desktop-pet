"""Cross-process queue and reply behavior without a desktop window."""

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from notification_store import NotificationStore


class NotificationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "notifications.sqlite3"
        self.sender = NotificationStore(self.path)
        self.pet = NotificationStore(self.path)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_fifo_reply_and_restart(self) -> None:
        first = self.sender.create("Codex", "完成", "任务结束", ["已查看", "稍后"])
        second = self.sender.create("Codex", "选择", "请选择下一步", [
            {"label": "方案A", "description": "保留当前桌宠动作，改动范围较小。", "recommended": True},
            {"label": "方案B", "description": "增加明显弹跳，提醒更醒目。"},
        ])
        self.assertEqual(self.pet.next_pending().id, first.id)
        self.pet.answer(first.id, 1)
        self.assertEqual(self.sender.get(first.id).result()["choice"], "稍后")
        self.assertEqual(self.pet.next_pending().id, second.id)
        reopened = NotificationStore(self.path)
        reopened.answer(second.id, 0)
        self.assertEqual(self.sender.get(second.id).result()["choice"], "方案A")
        self.assertIn("改动范围", self.sender.get(second.id).result()["choice_description"])
        self.assertEqual(reopened.get(second.id).choice_recommended, (True, False))
        self.assertIsNone(self.pet.next_pending())

    def test_dismissal_and_immutable_reply(self) -> None:
        notice = self.sender.create("Codex", "需确认", "请检查", ["确认"])
        self.pet.dismiss(notice.id)
        self.assertEqual(self.sender.get(notice.id).status, "dismissed")
        self.pet.answer(notice.id, 0)
        self.assertEqual(self.sender.get(notice.id).status, "dismissed")

    def test_text_migrates_an_existing_queue_and_delivers_only_one_reply(self) -> None:
        choice = self.sender.create("Codex", "选择", "请选择", ("确认",))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("DROP TABLE notice_text_replies")
        reopened = NotificationStore(self.path)
        text = reopened.create("Codex", "补充", "还有补充吗？", (), accepts_text=True)
        approval = reopened.create("Codex", "审批", "需要授权", ("知道了",), kind="approval")
        self.assertEqual(reopened.next_pending().id, approval.id)
        with self.assertRaisesRegex(ValueError, "outside available choices"):
            self.pet.answer(text.id, 0)
        for invalid in ("  \r\n ", "字" * 501, "测试\0输入"):
            with self.assertRaises(ValueError):
                self.pet.answer_text(text.id, invalid)
        self.assertFalse(self.pet.answer_text(choice.id, "不能替代选择"))
        self.assertFalse(self.pet.answer_text(approval.id, "不能替代授权"))
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda reply: self.pet.answer_text(text.id, reply),
                                        ("  中文回复\r\n下一行  ", "另一个回复")))
        self.assertEqual(sum(results), 1)
        self.assertFalse(self.pet.answer_text(text.id, "再次提交"))
        result = NotificationStore(self.path).get(text.id).result()
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["reply_text"], "中文回复\n下一行" if results[0] else "另一个回复")
        self.assertIsNone(result["choice"])
        self.assertTrue(self.pet.answer(choice.id, 0))
        self.assertNotIn("reply_text", self.pet.get(choice.id).result())

    def test_invalid_choices_do_not_enter_queue(self) -> None:
        with self.assertRaises(ValueError):
            self.sender.create("Codex", "选择", "请选择", ["A", "B", "C", "D"])
        with self.assertRaises(ValueError):
            self.sender.create("Codex", "选择", "请选择", ["同意", "同意"])
        with self.assertRaises(ValueError):
            self.sender.create("Codex", "选择", "请选择", [
                {"label": "方案A", "description": "方案A"},
                {"label": "方案B", "description": ""},
            ])
        with self.assertRaisesRegex(ValueError, "20 display columns"):
            self.sender.create("Codex", "选择", "请选择", [
                {"label": "自动隐藏后重新打开查看", "description": "提醒自动收起，可稍后重新打开查看。"},
                {"label": "保留到手动关闭", "description": "提醒一直显示，直到你手动关闭。"},
            ])
        with self.assertRaisesRegex(ValueError, "at most one"):
            self.sender.create("Codex", "选择", "请选择", [
                {"label": "先做界面", "description": "先做界面，方便尽早检查交互。", "recommended": True},
                {"label": "先做服务", "description": "先做服务，方便尽早验证连接。", "recommended": True},
            ])
        self.assertIsNone(self.pet.next_pending())

    def test_legacy_completion_can_display_and_return_text_by_its_original_id(self):
        legacy = self.sender.create("ChatGPT", "旧连接完成", "请查看成果。", ("知道了",), software="Codex")
        flags = {"client_id": "codex", "agent": "ChatGPT", "software": "Codex", "result_class": "brief"}
        self.sender.begin_turn("session", "turn", "question", client_id="codex")
        fallback = self.sender.create_completion_notice("session", "turn", **flags)
        approval = self.sender.create("ChatGPT", "审批", "请在客户端处理。", ("知道了",), kind="approval")
        self.assertTrue(fallback.accepts_text)
        self.assertFalse(approval.accepts_text)
        self.assertTrue(self.pet.answer_text(fallback.id, "补充一下。"))
        self.assertEqual(self.pet.take_host_reply_ids("session", "next", client_id="codex"), [fallback.id])
        self.assertTrue(self.pet.get(legacy.id).accepts_text)
        self.assertTrue(self.pet.answer_text(legacy.id, "收到。\n我会查看。"))
        self.assertFalse(self.pet.answer_text(legacy.id, "重复发送"))
        modern = self.sender.get(legacy.id).result()
        self.assertEqual(modern["reply_text"], "收到。\n我会查看。")
        self.assertIsNone(modern["choice"])
        with closing(sqlite3.connect(self.path)) as connection:
            selected, choices = connection.execute("SELECT selected_index, choices FROM notifications WHERE id=?",
                                                   (legacy.id,)).fetchone()
        legacy_reply = json.loads(choices)[selected]
        self.assertEqual(legacy_reply, {"label": "收到。\n我会查看。", "description": "虹夏文字回复"})

    def test_decision_accepts_one_preset_or_typed_answer_on_old_and_new_connections(self):
        options = [
            {"label": "预设甲", "description": "先核对本机界面的结果。"},
            {"label": "预设乙", "description": "先核对回复工具的结果。", "recommended": True},
            {"label": "预设丙", "description": "先核对通知队列的结果。"},
        ]
        for explicit in (False, True):
            notice = self.sender.create("Codex", "选择", "请选择或输入。", options, accepts_text=explicit)
            self.assertTrue(self.pet.get(notice.id).accepts_text)
            self.assertTrue(self.pet.answer_text(notice.id, "我建议一起检查。"))
            reply = self.pet.answer(notice.id, 0).result()
            self.assertEqual(reply["reply_text"], "我建议一起检查。")
            self.assertIsNone(reply["choice"])
            if not explicit:
                with closing(sqlite3.connect(self.path)) as connection:
                    choice, choices = connection.execute("SELECT selected_index, choices FROM notifications WHERE id=?",
                                                         (notice.id,)).fetchone()
                self.assertEqual(choice, len(options))
                self.assertEqual(json.loads(choices)[choice]["description"], "虹夏文字回复")
            selected = self.sender.create("Codex", "选择", "请选择或输入。", options, accepts_text=explicit)
            self.assertEqual(self.pet.answer(selected.id, 1).result()["choice"], "预设乙")
            self.assertFalse(self.pet.answer_text(selected.id, "不能覆盖已点选的结果。"))

    def test_retention_expires_pending_and_removes_old_answers(self) -> None:
        started = 1_000_000
        with patch("notification_store.time.time", return_value=started):
            answered = self.sender.create("Codex", "完成", "任务结束", ["已查看"])
            pending = self.sender.create("Codex", "待选", "等待选择", ["确认"])
            self.pet.answer(answered.id, 0)
            text = self.sender.create("Codex", "文字", "请补充", (), accepts_text=True)
            self.pet.answer_text(text.id, "保留期验证")
        with patch("notification_store.time.time", return_value=started + 8 * 86400):
            self.pet.prune()
        self.assertIsNone(self.sender.get(answered.id))
        self.assertIsNone(self.sender.get(text.id))
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM notice_text_replies").fetchone()[0], 0)
        self.assertEqual(self.sender.get(pending.id).status, "pending")
        with patch("notification_store.time.time", return_value=started + 31 * 86400):
            self.pet.prune()
        self.assertEqual(self.sender.get(pending.id).status, "expired")


if __name__ == "__main__":
    unittest.main()
