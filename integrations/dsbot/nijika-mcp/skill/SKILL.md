---
name: nijika-dsbot-dialog
description: Use the local Nijika desktop pet MCP tools when a DS Bot task needs a short user choice or a completed result needs desktop review.
whenToUse: Load this skill at the end of every DS Bot assistant turn to check the completion-notice rule, and whenever a DS Bot task reaches a concrete user decision or reviewable result.
---

# Nijika desktop dialogue for DS Bot

The local tools are `mcp__nijika_pet__request_decision`,
`mcp__nijika_pet__show_completion`, `mcp__nijika_pet__get_reply`, and
`mcp__nijika_pet__wait_for_reply`.

## Required end-of-turn notice

Before every final DS Bot response, use `mcp__nijika_pet__show_completion`
once with a concrete summary of the result. This includes short factual
answers and user-requested JSON. Do not send a content-free “任务完成”.

Internal title generation, confirmed system-generated background work,
explicit subagent events, and missing valid turn state may remain quiet.
`show_completion` proves that a notice was queued; it does not prove the user
has seen or accepted it.

## Decisions

When the user must choose or review a short result, call
`mcp__nijika_pet__request_decision` before asking in chat. Put enough context
in the question for a decision from the bubble itself. Offer two or three
meaningful choices; give each a one-sentence description. Mark at most one
choice as recommended when it has a concrete advantage.

Use `wait_for_reply` with `timeout_seconds: 45` and repeat with the same
request ID while the turn remains active. A `pending` result means queued,
never approved. On `answered`, state the selected option in the DS Bot chat
and continue. If the turn ends first, retain the request ID and call
`get_reply` first on a resumed turn.

## Source identity

The installed DS Bot connection supplies `Agent` / `DS Bot`. Omit
`agent_name` and `software` in normal calls. Never guess a model name or copy
a Codex, DSH, or Work label into a DS Bot call. If the connection reports an
incorrect host after an upgrade, correct the DS Bot environment rather than
permanently hardcoding labels in every prompt.
