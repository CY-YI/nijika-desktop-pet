"""Codex completion fallback privacy, protocol and cross-process boundaries."""

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from approval_hook import handle_event, main
from codex_completion import completion_preview, prompt_class, result_class, tool_flags
from notification_store import NotificationStore


class CodexCompletionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "queue.sqlite3"
        self.store = NotificationStore(self.path)
        self.identity = {"session_id": "session-test", "turn_id": "turn-test"}

    def tearDown(self):
        self.directory.cleanup()

    def event(self, name, **fields):
        return {**self.identity, "hook_event_name": name, **fields}

    def begin(self, prompt="帮我检查工程并修复测试"):
        handle_event(self.event("UserPromptSubmit", prompt=prompt), self.store)

    def tool(self, name="Bash", response=None):
        handle_event(self.event("PostToolUse", tool_name=name,
                               tool_response=response), self.store)

    def stop(self, message="已完成修复，回归测试通过。"):
        return handle_event(self.event("Stop", last_assistant_message=message), self.store)

    def count(self):
        with contextlib.closing(sqlite3.connect(self.path)) as connection:
            return connection.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]

    def test_task_creates_one_result_preview_notice(self):
        self.begin()
        self.tool()
        request = self.stop()
        self.assertIsNotNone(request)
        notice = self.store.get(request)
        self.assertEqual((notice.agent, notice.title, notice.message, notice.choices), (
            "ChatGPT", "任务完成", "已完成修复，回归测试通过。", ("知道了",),
        ))
        self.assertEqual(notice.software, "Codex")
        self.assertEqual(notice.kind, "agent")
        self.assertIsNone(self.stop())
        self.assertEqual(self.count(), 1)

    def test_repeat_stop_after_click_close_and_prompt_replay_does_not_duplicate(self):
        for state in ("answered", "dismissed"):
            with self.subTest(state=state):
                self.identity["turn_id"] = state
                self.begin()
                request = self.stop()
                if state == "answered":
                    self.store.answer(request, 0)
                else:
                    self.store.dismiss(request)
                self.begin()  # a replay must not reset the durable sent flag
                self.assertIsNone(self.stop())
        self.assertEqual(self.count(), 2)

    def test_concurrent_stop_creates_exactly_one_notice(self):
        self.begin()
        event = self.event("Stop", last_assistant_message="已完成修复。")
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: handle_event(event, self.store), range(6)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(self.count(), 1)

    def test_failed_insert_does_not_consume_the_completion(self):
        self.begin()
        with contextlib.closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TRIGGER fail_notice BEFORE INSERT ON notifications "
                               "BEGIN SELECT RAISE(ABORT, 'test error'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.stop()
        with contextlib.closing(sqlite3.connect(self.path)) as connection, connection:
            self.assertEqual(connection.execute(
                "SELECT completion_notice_sent FROM codex_turn_state",
            ).fetchone()[0], 0)
            connection.execute("DROP TRIGGER fail_notice")
        self.assertIsNotNone(self.stop())

    def test_successful_nijika_completion_and_decision_suppress_fallback(self):
        for index, name in enumerate((
            "mcp__nijika-pet__show_completion", "mcp__nijika_pet__request_decision",
            "mcp__NIJIKA_WORK_PET__show_completion", "nijika-work-pet.request_decision",
        )):
            with self.subTest(name=name):
                self.identity["turn_id"] = str(index)
                self.begin()
                response = {"content": [{"type": "text", "text": json.dumps({
                    "request_id": "existing-notice", "status": "pending",
                })}]}
                self.tool(name, response)
                self.assertIsNone(self.stop())
        self.assertEqual(self.count(), 0)

    def test_invalid_or_unrelated_notice_and_reply_tools_do_not_suppress(self):
        for index, (name, response) in enumerate((
            ("mcp__nijika-pet__show_completion", {"request_id": None, "status": "invalid"}),
            ("mcp__nijika-pet__request_decision", {"isError": True, "content": []}),
            ("mcp__nijika-pet__show_completion", None),
            ("mcp__other__show_completion", {"request_id": "other", "status": "pending"}),
            ("mcp__nijika-pet__get_reply", {"request_id": "old", "status": "answered"}),
            ("mcp__nijika-pet__wait_for_reply", {"request_id": "old", "status": "pending"}),
        )):
            with self.subTest(name=name, response=response):
                self.identity["turn_id"] = str(index)
                self.begin()
                self.tool(name, response)
                self.assertIsNotNone(self.stop())

    def test_every_valid_reply_is_notified_once(self):
        for index, (prompt, reply) in enumerate((
            ("1+1等于几？", "2。"),
            ("What is the Python version?", "Python 3.12.8."),
            ("什么是 MCP？", "MCP 是一种工具连接协议。"),
            ("帮我修复功能", ""),
            ("帮我修复功能", None),
            ("帮我修复功能", "请选择先修改界面还是服务？"),
            ("Your task is to generate a short title for the following user prompt. "
             "Only return the title.", "已完成修复和测试"),
        )):
            with self.subTest(prompt=prompt):
                self.identity["turn_id"] = str(index)
                self.begin(prompt)
                self.tool()
                if prompt_class(prompt) != "internal":
                    self.assertIsNotNone(self.stop(reply))
                else:
                    self.assertIsNone(self.stop(reply))
        self.assertEqual(self.count(), 6)

    def test_simple_question_without_tool_still_creates_notice(self):
        self.begin("你好吗？")
        request = self.stop("我很好，谢谢。")
        self.assertIsNotNone(request)
        self.assertEqual(self.store.get(request).message, "我很好，谢谢。")

    def test_ambient_suggestions_background_output_is_quiet(self):
        self.begin("整理本项目的环境建议")
        output = json.dumps({
            "projectRoot": "C:/private/project",
            "generatedAtMs": 123456,
            "currentSuggestionIds": ["suggestion-1"],
            "suggestions": [{
                "appId": "codex-document-control",
                "title": "Open a document",
                "description": "Continue the document workflow.",
                "prompt": "Continue",
            }],
        })
        self.assertIsNone(self.stop(output))
        self.assertIsNone(self.stop(output))
        self.assertEqual(self.count(), 0)
        with contextlib.closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute(
                "SELECT completion_notice_sent FROM codex_turn_state",
            ).fetchone()[0], 1)

    def test_codex_private_helper_output_is_quiet_only_with_known_signature(self):
        helper_cwd = (
            "C:/Users/example/AppData/Local/OpenAI/Codex/bin/"
            "0ab0e7a8f3779036"
        )
        self.begin("Return the requested helper object.")
        event = self.event(
            "Stop", last_assistant_message='{"exclude":[]}', cwd=helper_cwd,
        )
        self.assertIsNone(handle_event(event, self.store))
        self.assertEqual(self.count(), 0)

        self.identity["turn_id"] = "user-json-in-helper-directory"
        self.begin("请返回一个 JSON 对象")
        event = self.event(
            "Stop", last_assistant_message='{"status":"ok"}', cwd=helper_cwd,
        )
        request = handle_event(event, self.store)
        self.assertIsNotNone(request)
        self.assertEqual(
            self.store.get(request).message, "已返回结构化结果，请查看任务。",
        )

    def test_user_requested_json_still_notifies_with_safe_preview(self):
        self.begin("请只返回一个 JSON 对象，不要调用工具")
        request = self.stop('{"status":"ok","items":[1,2,3]}')
        self.assertIsNotNone(request)
        self.assertEqual(
            self.store.get(request).message, "已返回结构化结果，请查看任务。",
        )
        self.assertNotIn('{"status"', self.store.get(request).message)

    def test_generic_user_suggestions_json_is_not_mistaken_for_ambient_work(self):
        self.begin("请返回两条改进建议，使用 JSON 数组")
        request = self.stop(json.dumps({"suggestions": [{
            "title": "改进文档",
            "description": "补充安装步骤",
            "prompt": "请补充安装步骤",
        }]}))
        self.assertIsNotNone(request)
        self.assertEqual(
            self.store.get(request).message, "已返回结构化结果，请查看任务。",
        )

    def test_structured_classification_boundaries(self):
        self.assertEqual(
            result_class(json.dumps({
                "projectRoot": "C:/project",
                "generatedAtMs": 123,
                "currentSuggestionIds": ["suggestion"],
                "suggestions": [{"appIds": ["connector_example"]}],
            })),
            "internal",
        )
        self.assertEqual(
            result_class('{"suggestions":[{"appId":"example"}]}'), "brief",
        )
        self.assertEqual(
            result_class(
                '{"generatedAtMs":123,"currentSuggestionIds":["x"],'
                '"suggestions":[{"title":"ordinary result"}]}',
            ),
            "brief",
        )
        self.assertEqual(
            result_class(
                '{"exclude":[]}',
                r"C:\Users\example\AppData\Local\OpenAI\Codex\bin\build",
            ),
            "internal",
        )
        self.assertEqual(result_class('{"status":"ok"}'), "brief")
        self.assertEqual(completion_preview('{"status":"ok"}'),
                         "已返回结构化结果，请查看任务。")

    def test_missing_or_blank_stop_message_still_creates_generic_notice(self):
        for message in (None, ""):
            with self.subTest(message=message):
                self.identity["turn_id"] = "missing-" + str(message)
                self.begin("1+1等于几？")
                request = self.stop(message)
                self.assertIsNotNone(request)
                self.assertEqual(self.store.get(request).message, "已完成本轮任务，请查看结果。")

    def test_no_prompt_or_invalid_identity_never_creates_notice(self):
        self.tool()
        self.assertIsNone(self.stop())
        for missing in ("session_id", "turn_id"):
            event = self.event("UserPromptSubmit", prompt="检查工程")
            event.pop(missing)
            handle_event(event, self.store)
            event = self.event("Stop", last_assistant_message="已完成检查")
            event.pop(missing)
            self.assertIsNone(handle_event(event, self.store))
        self.assertEqual(self.count(), 0)

    def test_resume_style_prompt_and_document_only_deliverable(self):
        self.begin("继续")
        self.tool("functions.exec_command")
        self.assertIsNotNone(self.stop("全部用例均为绿色。"))
        self.identity["turn_id"] = "documentation"
        self.begin("整理完整安装步骤")
        self.assertIsNotNone(self.stop(
            "1. 在客户端打开配置文件，先备份原有的服务定义，然后添加新的本机 MCP 服务。\n"
            "2. 保留原服务与权限设置，保存配置并重启客户端，再通过一条新任务验证工具可见、气泡显示和点击回传。"
        ))

    def test_distinct_session_or_turn_does_not_suppress_another_task(self):
        for session, turn in (("session-a", "same"), ("session-b", "same"), ("session-a", "next")):
            self.identity = {"session_id": session, "turn_id": turn}
            self.begin()
            self.assertIsNotNone(self.stop())
        self.assertEqual(self.count(), 3)

    def test_turn_metadata_never_persists_prompt_command_full_response_or_raw_ids(self):
        self.identity = {"session_id": "PRIVATE_SESSION_SENTINEL", "turn_id": "PRIVATE_TURN_SENTINEL"}
        self.begin("请检查 PRIVATE_PROMPT_SENTINEL")
        handle_event(self.event("PostToolUse", tool_name="Bash", tool_input={
            "command": "PRIVATE_COMMAND_SENTINEL", "description": "PRIVATE_REASON_SENTINEL",
        }, tool_response="PRIVATE_TOOL_OUTPUT_SENTINEL"), self.store)
        self.stop("已完成检查。PRIVATE_RESPONSE_SENTINEL")
        self.assertEqual(self.store.next_pending().message, "已完成检查。")
        for path in self.path.parent.glob("queue.sqlite3*"):
            self.assertNotIn(b"PRIVATE_", path.read_bytes())

    def test_completion_preview_redacts_links_paths_and_common_secret_shapes(self):
        preview = completion_preview(
            "已修复登录问题。API_KEY=supersecretvalue\n"
            "https://example.test/private C:\\Users\\person\\secret.txt "
            "PRIVATE_RESPONSE_SENTINEL"
        )
        self.assertIn("已修复登录问题", preview)
        for secret in ("supersecretvalue", "example.test", "Users", "PRIVATE_RESPONSE_SENTINEL"):
            self.assertNotIn(secret, preview)
        self.assertLessEqual(len(preview), 120)

    def test_completion_preview_skips_code_and_selects_first_useful_paragraph(self):
        self.assertEqual(
            completion_preview("```powershell\nGet-Secret\n```\n\n"
                               "1. 已修复本地提醒。\n2. 回归测试通过。\n\n后续信息不应进入预览。"),
            "已修复本地提醒。 回归测试通过。",
        )
        self.assertEqual(completion_preview("```powershell\nGet-Secret\n```"),
                         "已完成本轮任务，请查看结果。")

    def test_finished_tombstone_survives_notification_retention(self):
        with patch("notification_store.time.time", return_value=1_000_000):
            self.begin()
            request = self.stop()
            self.store.answer(request, 0)
        with patch("notification_store.time.time", return_value=1_000_000 + 31 * 86400):
            self.store.prune()
            self.assertIsNone(self.store.get(request))
            self.begin()
            self.assertIsNone(self.stop())
            self.assertEqual(self.count(), 0)

    def test_claude_source_ignores_all_completion_events(self):
        for event in (self.event("UserPromptSubmit", prompt="修复代码"),
                      self.event("Stop", last_assistant_message="已完成修复。")):
            self.assertIsNone(handle_event(event, self.store, "claude-code"))
        self.assertEqual(self.count(), 0)

    def test_explicit_notice_tombstone_survives_retention(self):
        with patch("notification_store.time.time", return_value=1_000_000):
            self.begin()
            self.tool("mcp__nijika-pet__show_completion", {"request_id": "already-sent", "status": "pending"})
        with patch("notification_store.time.time", return_value=1_000_000 + 31 * 86400):
            self.store.prune()
            self.begin()
            self.assertIsNone(self.stop())
        self.assertEqual(self.count(), 0)

    def test_explicit_subagent_is_ignored(self):
        self.begin()
        event = self.event("Stop", last_assistant_message="已完成修复", agent_id="child")
        self.assertIsNone(handle_event(event, self.store))
        self.assertIsNotNone(self.stop())

    def test_runner_stop_always_returns_no_op_json_even_on_bad_input_or_database(self):
        for payload in (b"bad JSON", b"[]", b"x" * (1024 * 1024 + 1),
                        json.dumps(self.event("Stop")).encode(),
                        json.dumps(self.event("Stop", last_assistant_message="已完成修复")).encode()):
            with self.subTest(length=len(payload)):
                output, errors = io.StringIO(), io.StringIO()
                with (patch("approval_hook.sys.stdin", io.TextIOWrapper(io.BytesIO(payload))),
                      patch("approval_hook.sys.argv", ["approval_hook.py", "--event", "Stop"]),
                      patch("approval_hook.NotificationStore", side_effect=sqlite3.OperationalError("private")),
                      contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
                    main()
                self.assertEqual(json.loads(output.getvalue()), {})
                self.assertEqual(errors.getvalue(), "")

    def test_prompt_and_tool_classification_boundaries(self):
        self.assertEqual(prompt_class("什么是单元测试？"), "question")
        self.assertEqual(prompt_class("能否帮我检查这次测试失败原因？"), "substantive")
        self.assertEqual(tool_flags("mcp__nijika_pet__show_completion", {
            "structuredContent": {"request_id": "example", "status": "pending"},
        }), (False, True))


if __name__ == "__main__":
    unittest.main()
