---
name: nijika-work-dialog
description: Use the Nijika desktop pet MCP tools in ChatGPT Work when a task needs the user to make a short decision or review a brief result on the desktop.
---

# Nijika Work dialogue

When a Work task needs a simple user decision, use the `nijika-work-pet` MCP server. Put the facts needed to decide in one concise desktop question and call `request_decision(task=..., question=..., options=...)`. Give two or three choices with a meaningful label and a one-sentence description of its effect. Keep the task under 30 characters, the question within 80 characters and three paragraphs, the label within 20 display columns, and each description within 6–48 characters. Correct a `status=invalid` response once and retry.

Call `wait_for_reply` or `get_reply` with the returned `request_id`. Continue the same task from an `answered` choice without asking for the same confirmation in chat. `pending` and `dismissed` are not approval. If the result is too substantial to judge from the bubble, use `show_completion` once to notify the user that a full review is needed; the acknowledgment does not approve the result. Do not send routine notices for simple facts.

If the Nijika MCP tools are unavailable in the current Work chat, explain that this chat does not have the desktop connection and continue in chat. Do not claim a desktop notice was delivered.
