"""Cross-process queue and reply behavior without a desktop window."""

import tempfile
import unittest
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
            {"label": "方案A", "description": "保留当前桌宠动作，改动范围较小。"},
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
        self.assertIsNone(self.pet.next_pending())

    def test_dismissal_and_immutable_reply(self) -> None:
        notice = self.sender.create("Codex", "需确认", "请检查", ["确认"])
        self.pet.dismiss(notice.id)
        self.assertEqual(self.sender.get(notice.id).status, "dismissed")
        self.pet.answer(notice.id, 0)
        self.assertEqual(self.sender.get(notice.id).status, "dismissed")

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
        self.assertIsNone(self.pet.next_pending())

    def test_retention_expires_pending_and_removes_old_answers(self) -> None:
        started = 1_000_000
        with patch("notification_store.time.time", return_value=started):
            answered = self.sender.create("Codex", "完成", "任务结束", ["已查看"])
            pending = self.sender.create("Codex", "待选", "等待选择", ["确认"])
            self.pet.answer(answered.id, 0)
        with patch("notification_store.time.time", return_value=started + 8 * 86400):
            self.pet.prune()
        self.assertIsNone(self.sender.get(answered.id))
        self.assertEqual(self.sender.get(pending.id).status, "pending")
        with patch("notification_store.time.time", return_value=started + 31 * 86400):
            self.pet.prune()
        self.assertEqual(self.sender.get(pending.id).status, "expired")


if __name__ == "__main__":
    unittest.main()
