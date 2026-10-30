---
name: nijika-work-dialog
description: Use the Nijika desktop pet MCP tools in ChatGPT Work when a task needs the user to make a short decision or review a brief result on the desktop.
---

# Nijika Work dialogue

When a Work task needs a simple user decision, use the `nijika-work-pet` MCP server. Put the facts needed to decide in one concise desktop question and call `request_decision(task=..., question=..., options=...)`. Give two or three choices with a meaningful label and a one-sentence description of its effect. If one option is preferable for a concrete reason, set its `recommended: true` and state that reason in its description; recommend at most one option. Keep the task under 30 characters, the question within 80 characters and three paragraphs, the label within 20 display columns, and each description within 6–48 characters. Correct a `status=invalid` response once and retry.

Before every final Work response, check this rule. If the task changed files, completed setup or tests, reached a diagnostic conclusion, produced multi-step guidance, or created another result the user should acknowledge, call `show_completion` once with the concrete outcome. A brief factual answer with no result or next action may remain quiet; do not send content-free “任务完成” text.

For a decision, call `wait_for_reply` with the returned `request_id` and `timeout_seconds: 45`. A pending request is queued, not confirmed visible; keep its ID and never send a duplicate while waiting. If one wait returns `pending`, repeat it with the **same request ID** for up to twelve waits (about nine minutes) while this Work turn remains active. One timeout is not a reason to finish the decision task. When answered, state the clicked choice visibly in the same Work chat and continue without asking for the same confirmation again. This is an assistant acknowledgment, not a new user message. `pending` and `dismissed` are not approval. If the result is too substantial to judge from the bubble, use `show_completion` once to notify the user that a full review is needed; the acknowledgment does not approve the result. Do not send routine notices for simple facts.

If the turn is interrupted or still pending after those waits, keep the request ID in the Work chat and explain that a later click is saved but an ended turn cannot wake itself. On the first resumed turn with an unresolved Nijika request ID, call `get_reply` for that ID **before** issuing another question or responding to “我回复了 / 继续”. State the selected option in the same Work chat and resume the original work. If the connection is unavailable, continue in chat.

If the Nijika MCP tools are unavailable in the current Work chat, explain that this chat does not have the desktop connection and continue in chat. Do not claim a desktop notice was delivered.

<!-- BEGIN NIJIKA-SOURCE-IDENTITY -->
Notification headers separate the Agent name from the host application. Keep `task` as the task name only, without Codex/DSH/Claude prefixes. If the connected tool schema exposes `agent_name` and `software`, provide the actual Agent identity and host when known, e.g. ChatGPT + Work, ChatGPT + Codex, Claude + VS Code, or ChatGPT + Obsidian. These are display labels, not authentication or permission. Do not infer a model from a multimodel host such as DSH or WorkBuddy; leave the Agent generic if unknown. An editor embedding the same engine needs its actual software label; the engine handshake alone cannot distinguish it. If an old tool schema lacks these fields, omit them and report that reloading the MCP is needed; never send unsupported arguments. Pending replies remain tied to their original request ID.
In the installed Work plugin, omit the optional identity fields; the plugin supplies `ChatGPT` / `Work`.
<!-- END NIJIKA-SOURCE-IDENTITY -->
