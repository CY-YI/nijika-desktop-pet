---
name: nijika-desktop-dialog
description: Shape Codex task-completion alerts and user decisions for the Nijika desktop pet MCP tools. Use when a Codex task needs the user to review a result or choose a next step through the desktop pet.
---

# Nijika desktop dialogue

Use the connected Nijika desktop pet MCP tools when a Codex task reaches a real review point or needs a user choice. The pet is a compact desktop surface; keep the full reasoning and evidence in the task, then distill what the user needs to act on into the bubble.

For a decision, call `request_decision(task=..., question=..., options=...)` with one concrete question and two or three mutually exclusive options. `task` is the short bubble title; do not substitute a `title` argument. Each option must have a meaningful short `label` and a one-sentence `description` of what selecting it will change, cost, or trade off. Replace bare “方案 A / 方案 B” with names that convey the difference. Use the user's existing decisions rather than asking the same thing again. If a safe default is clear, put it first and say why in its description. Keep the task title under 30 characters, question under 120 characters, labels within 10 display columns, and descriptions between 6 and 48 characters.

For a completed task that merits a desktop alert, call `show_completion(task=..., summary=...)`. `task` is the short bubble title, and `summary` states the concrete result and where to review it. Do not claim that sending the alert means the user has seen or approved the work.

The tools return a `request_id`. Use `wait_for_reply` or `get_reply` to read the actual desktop selection. A `pending` result means the user has not answered; `dismissed` means no option was chosen. Continue only according to the response and the task's existing authorization. Do not invent a choice after a timeout, and do not treat the act of displaying a question as approval.
