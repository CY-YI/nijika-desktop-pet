"""Verify a queued decision recovers when its bubble window becomes hidden."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from notification_store import NotificationStore
from pet import BubbleNotice, PetWindow, user32


class PetNotificationTests(unittest.TestCase):
    def test_hidden_pending_bubble_is_shown_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "notifications.sqlite3")
            pending = store.create("Codex", "下一步", "先做哪项？", [
                {"label": "先做界面", "description": "先确认交互，方便尽早调整。", "recommended": True},
                {"label": "先做服务", "description": "先验证连接，再制作交互。"},
            ])
            bubble = SimpleNamespace(
                notice=BubbleNotice("Codex · 下一步", "先做哪项？", request_id=pending.id),
                hwnd=123, show=Mock(), hide=Mock(),
            )
            window = object.__new__(PetWindow)
            window.notifications = store
            window.next_notice_poll = 0
            window.defer_next_notice_until = 0
            window.last_notice_show_log_at = 0
            window.bubble = bubble
            window.x = window.y = 0
            window.width = 320
            window.height = 480
            window.set_state = Mock()
            with patch.object(user32, "IsWindowVisible", return_value=False):
                window._poll_notifications(1.0)
            bubble.show.assert_called_once()
            self.assertEqual(bubble.show.call_args.args[0].action_recommended, (True, False))


if __name__ == "__main__":
    unittest.main()
