# Nijika desktop pet

For a Codex task that needs the user's review or a concrete decision, use the installed `nijika-desktop-dialog` skill and the `nijika-pet` MCP tools to send a concise desktop notice. A deliverable explicitly requested for review counts: send `show_completion` once before the final chat response. Do not send routine notices for simple factual replies.

For a decision, call `request_decision` before asking in chat. Give each choice a meaningful label of at most 20 display columns (about 10 Chinese characters) and a one-sentence description of its effect. If the tool returns `status=invalid`, correct the stated input problem and retry once. Do not treat a pending or dismissed notice as approval.

If the skill file cannot be read but the MCP tools are available, use the tool schemas and these rules. A failed skill read does not mean the MCP tools are unavailable. If the MCP tools are unavailable or the corrected call still fails, continue in chat without blocking the task.
