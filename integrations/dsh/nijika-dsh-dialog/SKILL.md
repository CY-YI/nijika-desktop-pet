---
name: nijika-dsh-dialog
description: Use the local Nijika desktop pet MCP tools when a DSH task needs a short user choice or a completed result needs desktop review.
whenToUse: A DSH task reaches a concrete user decision, short deliverable review, or substantive completion that the user should notice on the desktop.
---

# Nijika desktop dialogue for DSH

The tools are `mcp__nijika_pet__request_decision`, `mcp__nijika_pet__show_completion`, `mcp__nijika_pet__get_reply`, and `mcp__nijika_pet__wait_for_reply`. Use them for DSH work that needs the user's attention. A brief factual answer with no deliverable or next action does not need a desktop notice.

For a decision, put the facts needed to choose in `question`. Give two or three meaningful labels rather than “方案 A / B”; each option needs one sentence describing its effect. Labels fit within 20 display columns (about 10 Chinese characters), task titles within 30 characters, questions within 80 characters, and descriptions within 6–48 characters. Mark at most one option `recommended: true`, only when its description explains a concrete advantage. If `status=invalid`, correct the stated input issue and retry once.

For a short result that fits in the bubble, use `request_decision` with the full result and concrete choices such as “接受结果” and “需要修改”. Wait for the desktop click, state the selected option visibly in the same DSH conversation, and continue without another confirmation. For a result too large for the bubble, call `show_completion` once before the final chat response with a concrete summary and where to review it. A completion click acknowledges receipt; it is not approval.

`pending` means queued locally, not confirmed visible or approved. Keep the request ID and do not resend an identical notice while it is pending. Use `get_reply` or `wait_for_reply` for a decision; `dismissed` is not a choice. If the tools are unavailable or the corrected call still fails, continue in the DSH chat and state that the desktop notification could not be delivered.
