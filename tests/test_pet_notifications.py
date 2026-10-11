"""Verify a queued decision recovers when its bubble window becomes hidden."""

import ctypes
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from notification_store import NotificationStore
from pet import BubbleNotice, BubbleOverlay, PetWindow, user32, SWP_SHOWWINDOW


class PetNotificationTests(unittest.TestCase):
    def test_bubble_reuses_registered_window_class(self) -> None:
        bubble = BubbleOverlay(Mock(), Mock())
        with (patch.object(user32, "RegisterClassW", return_value=0),
              patch.object(ctypes, "get_last_error", return_value=1410),
              patch.object(user32, "CreateWindowExW", return_value=123)):
            bubble._ensure_window()
        self.assertEqual(bubble.hwnd, 123)

    def test_hidden_pending_bubble_is_shown_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "notifications.sqlite3")
            pending = store.create("Codex", "下一步", "先做哪项？", [
                {"label": "先做界面", "description": "先确认交互，方便尽早调整。", "recommended": True},
                {"label": "先做服务", "description": "先验证连接，再制作交互。"},
            ])
            bubble = SimpleNamespace(
                notice=BubbleNotice("Codex · 下一步", "先做哪项？", request_id=pending.id),
                hwnd=123, show=Mock(), hide=Mock(), ensure_display=Mock(return_value=False),
            )
            window = object.__new__(PetWindow)
            window.notifications = store
            window.next_notice_poll = 0
            window.defer_next_notice_until = 0
            window.last_notice_show_log_at = 0
            window.last_logged_notice_id = None
            window.bubble = bubble
            window.x = window.y = 0
            window.width = 320
            window.height = 480
            window.set_state = Mock()
            with patch.object(user32, "IsWindowVisible", return_value=False):
                window._poll_notifications(1.0)
            bubble.show.assert_called_once()
            self.assertEqual(bubble.show.call_args.args[0].action_recommended, (True, False))

    def test_hidden_or_moved_window_is_repaired_without_repainting(self):
        bubble = BubbleOverlay(Mock(), Mock())
        bubble.hwnd = 123
        bubble.width, bubble.height = 430, 180
        def fill_rect(hwnd, pointer):
            rect = pointer._obj
            rect.left, rect.top, rect.right, rect.bottom = 20, 30, 450, 210
            return True
        with (patch.object(user32, "IsWindow", return_value=True),
              patch.object(bubble, "_position", return_value=(20, 30)),
              patch.object(user32, "SetWindowPos", return_value=True) as move,
              patch.object(user32, "IsWindowVisible", return_value=True),
              patch.object(user32, "GetWindowRect", side_effect=fill_rect)):
            self.assertTrue(bubble.ensure_display((10, 10, 320, 480)))
        self.assertTrue(move.call_args.args[-1] & SWP_SHOWWINDOW)

    def test_poll_exception_does_not_skip_health_or_later_poll(self):
        window = object.__new__(PetWindow)
        window.last_notice_error_at = 0
        window._poll_notifications = Mock(side_effect=[RuntimeError("failure"), None])
        window._write_notification_health = Mock()
        with patch("pet.log_notice_event"):
            window.poll_notifications_safely()
            window.poll_notifications_safely()
        self.assertEqual(window._poll_notifications.call_count, 2)
        self.assertEqual(window._write_notification_health.call_count, 2)

    def test_approval_ack_only_records_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "notifications.sqlite3")
            pending = store.create("Codex", "命令需要授权", "请在 Codex 授权", ["知道了"], kind="approval")
            window = object.__new__(PetWindow)
            window.notifications = store
            window.bubble = SimpleNamespace(show=Mock())
            window.set_state = Mock()
            window.x = window.y = 0
            window.width, window.height = 320, 480
            notice = BubbleNotice("审批", pending.message, actions=pending.choices,
                                  kind="approval", request_id=pending.id)
            window._bubble_action(notice, 0)
            self.assertEqual(store.get(pending.id).result()["choice"], "知道了")
            self.assertIn("Codex 审批卡授权", window.bubble.show.call_args.args[0].text)


if __name__ == "__main__":
    unittest.main()
