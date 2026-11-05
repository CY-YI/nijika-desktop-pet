import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from approval_hook import handle_event, main
from notification_store import NotificationStore


class ApprovalHookTests(unittest.TestCase):
    def test_approval_priority_dedup_and_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "queue.sqlite3")
            normal = store.create("Codex", "成果", "查看结果", ["知道了"])
            event = {"hook_event_name": "PermissionRequest", "session_id": "test-session",
                     "turn_id": "test-turn", "tool_name": "Bash", "cwd": "C:/test-project",
                     "tool_input": {"command": "command with TEST_SECRET", "description": "reason"}}
            request = handle_event(event, store)
            self.assertEqual(handle_event(event, store), request)
            self.assertEqual(store.next_pending().id, request)
            self.assertEqual(store.get(request).kind, "approval")
            self.assertNotIn("TEST_SECRET", store.get(request).message)
            self.assertIn("不授予权限", store.get(request).message)
            event["hook_event_name"] = "PostToolUse"
            event["tool_input"].pop("description")
            handle_event(event, store)
            self.assertEqual(store.get(request).status, "resolved")
            self.assertIsNone(store.get(request).selected_index)
            self.assertEqual(store.next_pending().id, normal.id)

    def test_ack_is_not_permission_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "queue.sqlite3")
            request = handle_event({"hook_event_name": "PermissionRequest"}, store)
            self.assertEqual(store.answer(request, 0).result()["choice"], "知道了")
            self.assertEqual(store.get(request).status, "answered")
            self.assertEqual(store.get(request).kind, "approval")

    def test_both_approval_hosts_have_separate_agent_and_software(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NotificationStore(Path(directory) / "queue.sqlite3")
            for caller, expected in (("codex", ("ChatGPT", "Codex")),
                                     ("claude-code", ("Claude", "Claude Code"))):
                request = handle_event({"hook_event_name": "PermissionRequest",
                                        "session_id": caller}, store, caller)
                notice = store.get(request)
                self.assertEqual((notice.agent, notice.software), expected)

    def test_runner_never_outputs_approval_or_raw_input(self):
        output, errors = io.StringIO(), io.StringIO()
        with (patch("approval_hook.sys.stdin", io.TextIOWrapper(io.BytesIO(b'invalid input'))),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
            main()
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("invalid input", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
