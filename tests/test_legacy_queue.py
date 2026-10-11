import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legacy_queue import LegacyQueueBridge
from notification_store import NotificationStore, default_database_path


class LegacyQueueTests(unittest.TestCase):
    def test_msix_localappdata_does_not_change_shared_path(self):
        with (patch.dict(os.environ, {"LOCALAPPDATA": "C:/package/private/cache"}),
              patch("notification_store.Path.home", return_value=Path("C:/test-user"))):
            os.environ.pop("NIJIKA_PET_DB_PATH", None)
            self.assertEqual(default_database_path(), Path("C:/test-user/.nijika-desktop-pet/notifications.sqlite3"))

    def test_old_mcp_queue_and_click_survive_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            old = NotificationStore(Path(directory) / "old.sqlite3")
            current = NotificationStore(Path(directory) / "new.sqlite3")
            bridge = LegacyQueueBridge(current, [old.path])
            request = old.create("Codex", "选择", "下一步", ["先做界面", "先做服务"])
            bridge.sync()
            bridge.sync()
            self.assertEqual(current.next_pending().id, request.id)
            current.answer(request.id, 0)
            bridge.sync()
            self.assertEqual(old.get(request.id).result()["choice"], "先做界面")
            self.assertIsNone(current.next_pending())

    def test_old_reply_and_source_failure_do_not_resurrect_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            old = NotificationStore(Path(directory) / "old.sqlite3")
            current = NotificationStore(Path(directory) / "new.sqlite3")
            request = old.create("DSH", "选择", "下一步", ["同意"])
            invalid = Path(directory) / "broken.sqlite3"
            invalid.write_text("invalid sqlite data")
            bridge = LegacyQueueBridge(current, [invalid, old.path])
            self.assertTrue(bridge.sync())
            self.assertEqual(current.next_pending().id, request.id)
            old.answer(request.id, 0)
            bridge.sync()
            self.assertEqual(current.get(request.id).result()["choice"], "同意")
            self.assertIsNone(current.next_pending())


if __name__ == "__main__":
    unittest.main()
