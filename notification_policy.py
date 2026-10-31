"""Shared, text-only notification policy for all lifecycle adapters.

Payloads are inspected in memory only. No transcript is read, and callers pass
only the resulting categories/flags to the local queue.
"""

from __future__ import annotations

import json
import re


_PREVIEW_LIMIT = 120
_QUESTION = re.compile(
    r"^(?:请问|什么|为什么|为何|怎么|如何|能否|是否|可不可以|"
    r"what\b|why\b|how\b|can\b|could\b|is\b|are\b|do\b|does\b)", re.I,
)
_ACTION = (
    r"修改|实现|修复|开发|创建|构建|运行|测试|部署|提交|推送|检查|排查|诊断|"
    r"更新|生成|制作|安装|配置|重构|验证|查验|分析|审查|审阅|优化|打包|整理|汇总|设计|编写"
)
_WORK_REQUEST = re.compile(
    rf"^(?:请|帮我|给我|麻烦|现在|先|继续|开始|再|一下|\s)*(?:{_ACTION})"
    rf"|(?:请|帮我|给我|希望你|要求你).{{0,35}}(?:{_ACTION})"
    r"|^(?:please\s+)?(?:build|edit|fix|create|implement|test|run|deploy|commit|"
    r"push|check|review|debug|configure|install|write|summarize)\b", re.I,
)
_INTERNAL_TITLE = re.compile(
    r"(?:your (?:job|task) is to|you (?:must|should|need to)).{0,60}"
    r"generate (?:a |an )?(?:short |concise |brief )?(?:ui |task )?title", re.I,
)
_RESULT = re.compile(
    r"已(?:完成|修复|修改|更新|生成|创建|配置|验证|检查|打包|整理|提交|推送|通过)"
    r"|(?:检查|测试|诊断|审查|验证)(?:结果|通过|发现|结论)"
    r"|(?:文件|配置|代码|接口|用例).{0,30}(?:完成|通过|失败|异常|问题|修复)"
    r"|\b(?:implemented|fixed|updated|created|configured|verified|passed|"
    r"tests? pass|test results?|review findings?|diagnosis)\b", re.I,
)
_WAITING = re.compile(
    r"^(?:请(?:先)?(?:确认|选择|提供|告诉)|等待(?:你|用户)|需要你(?:先)?(?:确认|选择|提供))"
    r"|(?:你(?:想|希望)|要不要|选哪个|哪一项|可以吗).{0,40}[?？]$"
    r"|^(?:please (?:choose|confirm|provide)|waiting for (?:you|your)|"
    r"which .{0,60}\?)", re.I,
)
_CODEX_HELPER_BIN = re.compile(
    r"(?:^|/)appdata/local/openai/codex/bin/[^/]+/?$", re.I,
)
_AMBIENT_SUGGESTION_ITEM_KEYS = {
    "appId", "appIds",
}
_AMBIENT_SUGGESTION_MARKERS = {
    "currentSuggestionIds", "generatedAtMs", "projectRoot",
}
_STEP = re.compile(r"^\s*(?:\d+[.)、]|[-*]\s+)\s*\S", re.M)
_FENCED_CODE = re.compile(r"```.*?(?:```|$)", re.S)
_URL = re.compile(r"(?:https?|ftp)://[^\s<>\"]+|www\.[^\s<>\"]+", re.I)
_WINDOWS_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\)[^\s，。；;！？!?]+"
)
_LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home|var|tmp|opt|etc|mnt|srv)/[^\s，。；;！？!?]+",
    re.I,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password|"
    r"passwd|authorization|cookie|session(?:[_-]?id)?|private[_-]?key)\b"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;，；]+)",
    re.I,
)
_SECRET_TOKEN = re.compile(
    r"\b(?:sk-|ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{8,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
    r"|\b[A-Fa-f0-9]{32,}\b"
    r"|\b[A-Z][A-Z0-9_]{7,}\b"
)
_REDACTION = "[已隐藏]"
_STRUCTURED_RESULT = "已返回结构化结果，请查看任务。"


def _structured_json(value: object) -> dict | list | None:
    if not isinstance(value, str) or len(value) > 1024 * 1024:
        return None
    clean = value.strip()
    if not clean.startswith(("{", "[")):
        return None
    try:
        parsed = json.loads(clean)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _is_codex_helper_cwd(value: object) -> bool:
    """Recognize Codex's private helper executable directory in memory only."""
    if not isinstance(value, str):
        return False
    return _CODEX_HELPER_BIN.search(value.replace("\\", "/")) is not None


def _is_ambient_suggestions(value: object) -> bool:
    parsed = _structured_json(value)
    if not isinstance(parsed, dict) or "suggestions" not in parsed:
        return False
    # Current Codex ambient suggestions have a distinctive persisted shape:
    # generatedAtMs/currentSuggestionIds/projectRoot plus items carrying an
    # appId or appIds. Requiring the two strongest markers avoids treating a
    # user's ordinary {"suggestions": [...]} deliverable as background work.
    if not {"currentSuggestionIds", "generatedAtMs"}.issubset(parsed):
        return False
    suggestions = parsed.get("suggestions")
    if not isinstance(suggestions, list):
        return False
    has_app_binding = any(
        isinstance(item, dict) and _AMBIENT_SUGGESTION_ITEM_KEYS.intersection(item)
        for item in suggestions[:20]
    )
    return has_app_binding and bool(
        _AMBIENT_SUGGESTION_MARKERS.intersection(parsed),
    )


def internal_completion(value: object, cwd: object = None) -> bool:
    """Return true only for known Codex background-task outputs."""
    if _is_ambient_suggestions(value):
        return True
    parsed = _structured_json(value)
    return (_is_codex_helper_cwd(cwd)
            and isinstance(parsed, dict)
            and parsed == {"exclude": []})


def prompt_class(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    clean = " ".join(value.split())
    if (_INTERNAL_TITLE.search(clean[:1500])
            and re.search(r"user prompt|task.*(?:UI|title)|only.*title", clean, re.I)):
        return "internal"
    if _WORK_REQUEST.search(clean):
        return "substantive"
    if len(clean) <= 200 and (_QUESTION.match(clean) or clean.endswith(("?", "？", "吗"))):
        return "question"
    return "unknown"


def result_class(value: object, cwd: object = None, *, client_id: str = "codex") -> str:
    # Stop may omit or blank the latest assistant text. Treat that as a
    # completed turn with a generic preview so short replies are not lost.
    if not isinstance(value, str) or not value.strip():
        return "brief"
    if client_id == "codex" and internal_completion(value, cwd):
        return "internal"
    clean = " ".join(value.split())
    if len(clean) < 240 and _WAITING.search(clean) and not _RESULT.search(clean):
        return "waiting"
    if _RESULT.search(clean):
        return "deliverable"
    if (len(_STEP.findall(value)) >= 2 and len(clean) >= 80
            or len(clean) >= 400 or "```" in value and len(clean) >= 120):
        return "deliverable"
    return "brief"


def completion_preview(value: object) -> str:
    """Derive a short, action-oriented preview without persisting the reply.

    The lifecycle hook receives the final reply only in memory. This function
    removes code, links, local paths and common secret shapes before selecting
    the first useful paragraph for the local notification database.
    """
    fallback = "已完成本轮任务，请查看结果。"
    if not isinstance(value, str) or not value.strip():
        return fallback
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = _FENCED_CODE.sub("\n", text)
    # Structured replies are valid user deliverables, but their raw JSON can
    # be long, private or unreadable in a small bubble. Keep the notification
    # while replacing only the preview text with an action-oriented summary.
    if _structured_json(text) is not None:
        return _STRUCTURED_RESULT
    paragraphs = re.split(r"\n\s*\n", text)
    candidate = ""
    for paragraph in paragraphs:
        lines = []
        for line in paragraph.splitlines():
            line = line.strip()
            if not line or re.fullmatch(r"[-*_=#>`\s]+", line):
                continue
            line = re.sub(r"^(?:#{1,6}\s+|(?:[-*]|\d+[.)、])\s+)", "", line)
            lines.append(line)
        if lines:
            candidate = " ".join(lines)
            if re.search(r"[\u3400-\u9fff]|[A-Za-z]{2}", candidate):
                break
    if not candidate:
        return fallback
    candidate = _URL.sub(_REDACTION, candidate)
    candidate = _WINDOWS_PATH.sub(_REDACTION, candidate)
    candidate = _LOCAL_PATH.sub(_REDACTION, candidate)
    candidate = _EMAIL.sub(_REDACTION, candidate)
    candidate = _BEARER.sub("Bearer " + _REDACTION, candidate)
    candidate = _SECRET_ASSIGNMENT.sub(lambda match: match.group(1) + "=" + _REDACTION, candidate)
    candidate = _SECRET_TOKEN.sub(_REDACTION, candidate)
    candidate = re.sub(r"(?:\s*\[已隐藏\]\s*){2,}", " " + _REDACTION + " ", candidate)
    candidate = re.sub(r"^(?:\[已隐藏\][\s,;，；:：]*)+", "", candidate)
    candidate = re.sub(r"(?:[\s,;，；:：]*\[已隐藏\])+$", "", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" \t-:：;；,，")
    if not candidate or not re.search(r"[\u3400-\u9fff]|[A-Za-z]{2}", candidate):
        return fallback
    if len(candidate) > _PREVIEW_LIMIT:
        candidate = candidate[: _PREVIEW_LIMIT - 1].rstrip() + "…"
    return candidate


def tool_flags(name: object, response: object) -> tuple[bool, bool]:
    """Return work/notice flags; only successful Nijika notices suppress Stop."""
    if not isinstance(name, str):
        return False, False
    normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    notice_tool = re.search(
        r"(?:^|_)nijika_(?:work_)?pet_(?:show_completion|request_decision)$", normalized,
    ) is not None
    work_tool = normalized in {
        "bash", "apply_patch", "edit", "write", "exec_command", "functions_exec_command",
        "write_stdin", "functions_write_stdin",
    } or normalized.endswith(("_read_file", "_write_file", "_edit_file"))
    return work_tool, notice_tool and _notice_created(response)


def _notice_created(value: object, depth: int = 0) -> bool:
    if depth > 6:
        return False
    if isinstance(value, dict):
        status = value.get("status")
        if value.get("isError") is True or isinstance(status, str) and status in {"invalid", "error", "failed"}:
            return False
        if (isinstance(value.get("request_id"), str) and value["request_id"]
                and isinstance(status, str) and status in {"pending", "answered", "dismissed", "expired"}):
            return True
        return any(_notice_created(value.get(key), depth + 1) for key in (
            "structuredContent", "structured_content", "content", "result", "text",
        ))
    if isinstance(value, list):
        return any(_notice_created(item, depth + 1) for item in value[:10])
    if isinstance(value, str) and len(value) <= 65536:
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return False
        return _notice_created(parsed, depth + 1)
    return False
