"""Conservative, text-only completion classification for Codex lifecycle hooks.

Payloads are inspected in memory only. No transcript is read, and callers pass
only the resulting categories/flags to the local queue.
"""

from __future__ import annotations

import json
import re


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
_STEP = re.compile(r"^\s*(?:\d+[.)、]|[-*]\s+)\s*\S", re.M)


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


def result_class(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "empty"
    clean = " ".join(value.split())
    if len(clean) < 240 and _WAITING.search(clean) and not _RESULT.search(clean):
        return "waiting"
    if _RESULT.search(clean):
        return "deliverable"
    if (len(_STEP.findall(value)) >= 2 and len(clean) >= 80
            or len(clean) >= 400 or "```" in value and len(clean) >= 120):
        return "deliverable"
    return "brief"


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
