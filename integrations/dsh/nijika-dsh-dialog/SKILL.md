---
name: nijika-dsh-dialog
description: Use the local Nijika desktop pet MCP tools when a DSH task needs a short user choice or a completed result needs desktop review.
whenToUse: Load this skill at the end of every DSH assistant turn to check the completion-notice rule, and whenever a DSH task reaches a concrete user decision or a reviewable result.
---

# Nijika desktop dialogue for DSH

The tools are `mcp__nijika_pet__request_decision`, `mcp__nijika_pet__show_completion`, `mcp__nijika_pet__get_reply`, and `mcp__nijika_pet__wait_for_reply`. Use them at the end of every reply in a valid DSH turn, including a brief factual answer or a blank/omitted final text; only internal title generation and missing valid turn state stay quiet.

## End-of-turn notice

Before sending every final DSH response, check this section. For every non-empty final DSH reply, call `show_completion` once with the concrete outcome, including a one-sentence factual answer. Internal title generation and missing valid turn state may remain quiet. Do not send a content-free “任务完成” notice and do not assume the lack of a DSH Stop hook creates a fallback.

For a decision, put the facts needed to choose in `question`. Give two or three meaningful labels rather than “方案 A / B”; each option needs one sentence describing its effect. Labels fit within 20 display columns (about 10 Chinese characters), task titles within 30 characters, questions within 80 characters, and descriptions within 6–48 characters. Mark at most one option `recommended: true`, only when its description explains a concrete advantage. If `status=invalid`, correct the stated input issue and retry once.

For a short result that fits in the bubble, use `request_decision` with the full result and concrete choices such as “接受结果” and “需要修改”. Wait for the desktop click, state the selected option visibly in the same DSH conversation, and continue without another confirmation. For a result too large for the bubble, call `show_completion` once before the final chat response with a concrete summary and where to review it. A completion click acknowledges receipt; it is not approval.

`pending` means queued locally, not confirmed visible or approved. Keep the request ID and do not resend an identical notice while it is pending. For a decision, call `wait_for_reply` with `timeout_seconds: 45` (below DSH's 60-second MCP call timeout). If it returns `pending`, call it again with the **same request ID**. Continue for up to twelve waits (about nine minutes) while this DSH turn remains active; one timeout is not a reason to finish the task or pretend a choice was made. `dismissed` is not a choice. If the wait is interrupted or still pending after twelve waits, clearly say that the click remains saved but this DSH turn cannot wake itself; keep the request ID in the conversation and tell the user they can send “继续” in this same DSH chat after clicking.

At the start of any resumed DSH turn, if the conversation contains an unresolved Nijika request ID, call `get_reply` for that ID **before** asking the question again or processing a generic “我回复了 / 继续” message. When `answered`, state the selected option visibly in this DSH chat and continue the original task. If the tools are unavailable or the corrected call still fails, continue in chat and state that the desktop notification could not be delivered.

<!-- BEGIN NIJIKA-SOURCE-IDENTITY -->
Notification headers separate the Agent name from the host application. Keep `task` as the task name only, without Codex/DSH/Claude prefixes. If the connected tool schema exposes `agent_name` and `software`, provide the actual Agent identity and host when known, e.g. ChatGPT + Work, ChatGPT + Codex, Claude + VS Code, or ChatGPT + Obsidian. These are display labels, not authentication or permission. Do not infer a model from a multimodel host such as DSH or WorkBuddy; leave the Agent generic if unknown. An editor embedding the same engine needs its actual software label; the engine handshake alone cannot distinguish it. If an old tool schema lacks these fields, omit them and report that reloading the MCP is needed; never send unsupported arguments. Pending replies remain tied to their original request ID.
For the standard DSH connection, omit `agent_name` and `software` in every call. The installed environment already supplies `Agent` / `DSH`. Never pass `Codex`, `ChatGPT`, `Work`, `DSH`, or `WorkBuddy` as `agent_name`; the server will reject that stale label as generic `Agent`. Pass a real model identity such as `DeepSeek` only when it is directly known.
<!-- END NIJIKA-SOURCE-IDENTITY -->
