"""Cross-client lifecycle invariants, with no real client configuration writes."""
import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from approval_hook import main
from notification_lifecycle import handle_lifecycle
from notification_store import NotificationStore


class NotificationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "queue.sqlite3"
        self.store = NotificationStore(self.path)

    def event(self, name, client="dsh", **fields):
        return {"version": 1, "event": name, "client_id": client,
                "session_id": "same-session", "turn_id": "same-turn",
                "origin": "user", **fields}

    def count(self):
        with contextlib.closing(sqlite3.connect(self.path)) as connection:
            return connection.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]

    def test_same_contract_for_all_known_clients_with_no_cross_client_suppression(self):
        for client, identity, software in (
            ("codex", "ChatGPT", "Codex"), ("dsh", "Agent", "DSH"),
            ("work", "ChatGPT", "Work"), ("claude-code", "Claude", "Claude Code"),
            ("gemini", "Gemini", "Gemini CLI"), ("copilot-cli", "Copilot", "Copilot CLI"),
            ("vscode", "Agent", "VS Code"),
        ):
            with self.subTest(client=client):
                handle_lifecycle(self.event("turn_started", client), self.store)
                event = self.event("turn_completed", client, last_assistant_message="已验证当前任务。")
                request = handle_lifecycle(event, self.store)
                notice = self.store.get(request)
                self.assertEqual((notice.agent, notice.software), (identity, software))
                self.assertEqual(notice.message, "已验证当前任务。")
                self.assertIsNone(handle_lifecycle(event, self.store))
        self.assertEqual(self.count(), 7)

    def test_adversarial_codex_raw_session_cannot_collide_with_other_client_namespace(self):
        for event in (
            self.event("turn_started", "codex", session_id=json.dumps(["dsh", "same-session"])),
            self.event("turn_started"),
        ):
            handle_lifecycle(event, self.store)
        for event in (
            self.event("turn_completed", "codex", session_id=json.dumps(["dsh", "same-session"])),
            self.event("turn_completed"),
        ):
            self.assertIsNotNone(handle_lifecycle(event, self.store))

    def test_reopened_store_and_concurrent_delivery_create_one_notice(self):
        handle_lifecycle(self.event("turn_started"), self.store)
        event = self.event("turn_completed", last_assistant_message="已完成并发验证。")
        reopened = NotificationStore(self.path)
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: handle_lifecycle(event, reopened), range(6)))
        self.assertEqual(sum(item is not None for item in results), 1)
        self.store.dismiss(next(item for item in results if item))
        self.assertIsNone(handle_lifecycle(event, NotificationStore(self.path)))
        self.assertEqual(self.count(), 1)

    def test_valid_tool_receipt_suppresses_but_failed_tool_does_not(self):
        handle_lifecycle(self.event("turn_started"), self.store)
        notice = self.store.create("Agent", "测试结果", "已通过主动通知测试。", ["知道了"], software="DSH")
        handle_lifecycle(self.event("tool_finished", tool_name="mcp__nijika_pet__show_completion",
                         tool_response={"structuredContent": {"request_id": notice.id, "status": "pending"}}),
                         self.store)
        self.assertIsNone(handle_lifecycle(self.event("turn_completed"), self.store))
        handle_lifecycle(self.event("turn_started", turn_id="failed"), self.store)
        handle_lifecycle(self.event("tool_finished", turn_id="failed",
                         tool_name="mcp__nijika_pet__show_completion",
                         tool_response={"request_id": None, "status": "invalid"}), self.store)
        self.assertIsNotNone(handle_lifecycle(self.event("turn_completed", turn_id="failed"), self.store))
        self.assertEqual(self.count(), 2)

    def test_missing_begin_background_subagent_and_bad_protocol_never_notify(self):
        self.assertIsNone(handle_lifecycle(self.event("turn_completed"), self.store))
        for origin in ("background", "subagent"):
            for name in ("turn_started", "turn_completed"):
                self.assertIsNone(handle_lifecycle(self.event(name, origin=origin), self.store))
        for fields in ({"version": True}, {"version": 2}, {"origin": "unknown"},
                       {"turn_id": ""}, {"session_id": None}, {"client_id": "../dsh"}):
            with self.assertRaises(ValueError):
                handle_lifecycle(self.event("turn_started", **fields), self.store)
        self.assertEqual(self.count(), 0)

    def test_codex_only_heuristic_does_not_silence_other_clients_user_json(self):
        message = json.dumps({"generatedAtMs": 1, "currentSuggestionIds": ["a"],
                              "suggestions": [{"appId": "test"}]})
        for client in ("codex", "dsh"):
            handle_lifecycle(self.event("turn_started", client), self.store)
            result = handle_lifecycle(self.event("turn_completed", client,
                                      last_assistant_message=message), self.store)
            if client == "codex":
                self.assertIsNone(result)
            else:
                self.assertEqual(self.store.get(result).message, "已返回结构化结果，请查看任务。")

    def test_old_codex_tombstone_still_suppresses_after_core_upgrade(self):
        with self.store._connect() as connection:
            connection.execute("INSERT INTO codex_turn_state VALUES (?,?,1,'unknown',0,0,1,1,1)",
                               (hashlib.sha256(b"same-session").hexdigest(),
                                hashlib.sha256(b"same-turn").hexdigest()))
        self.assertIsNone(handle_lifecycle(self.event("turn_completed", "codex"), self.store))
        self.assertEqual(self.count(), 0)

    def test_failed_insert_is_retryable_without_consuming_turn(self):
        handle_lifecycle(self.event("turn_started"), self.store)
        with self.store._connect() as connection:
            connection.execute("CREATE TRIGGER failed BEFORE INSERT ON notifications "
                               "BEGIN SELECT RAISE(ABORT, 'test'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            handle_lifecycle(self.event("turn_completed"), self.store)
        with self.store._connect() as connection:
            connection.execute("DROP TRIGGER failed")
        self.assertIsNotNone(handle_lifecycle(self.event("turn_completed"), self.store))

    def test_generic_cli_reports_failure_without_echoing_payload(self):
        output = io.StringIO()
        payload = b'{"PRIVATE_PAYLOAD":"do not log"}'
        with patch("approval_hook.sys.argv", ["hook", "--lifecycle"]), \
                patch("approval_hook.sys.stdin", io.TextIOWrapper(io.BytesIO(payload))), \
                patch("approval_hook.NotificationStore", return_value=self.store), \
                contextlib.redirect_stdout(output):
            main()
        self.assertEqual(json.loads(output.getvalue()), {"status": "failed", "request_id": None})


if __name__ == "__main__":
    unittest.main()
