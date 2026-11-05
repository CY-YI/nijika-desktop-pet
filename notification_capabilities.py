"""One capability vocabulary for setup, exported handoffs and the control UI."""
from __future__ import annotations


def notification_capability(client: str) -> dict:
    # Availability is a product capability, never proof of local trust,
    # lifecycle delivery or a notification having appeared on screen.
    available = client in {"codex", "dsh"}
    return {
        "protocol_version": 1,
        "mode": "event_available" if available else "active_only",
        "label": "可接结束事件 · 待独立验收" if available else "仅主动调用 · 无自动补发保障",
        "event_adapter": {"codex": "codex-native", "dsh": "dsh-session-events"}.get(client),
        "tested_host_version": "0.2.1-rc.2 / 0.2.1-rc.3" if client == "dsh" else None,
        "automatic_completion_verified": False,
        "requires_host_events": True,
        "explanation": (
            "共用虹夏通知核心。还需核对原生四事件安装、本人信任及真实新轮次；"
            "面板测试或一次 MCP 调用不能证明结束事件会自动触发。"
            if client == "codex" else
            "共用虹夏通知核心。向导安装 DSH 实时会话事件转接（接口核对版本 0.2.1-rc.2 / 0.2.1-rc.3），"
            "需重启并在新会话验证；不重放历史，不改变原生权限。其他 DSH 版本不推断已兼容。"
            if client == "dsh" else
            "共用虹夏 MCP 和通知核心，但当前未随本向导安装宿主结束事件适配；"
            "模型漏调仍可能没有提醒，安装 skill 不等于每轮自动补发。"
        ),
        "acceptance": [
            "客户端主动通知与桌面回执",
            "不主动调用 MCP 的短问答结束事件",
            "主动通知后同轮不重复",
            "后台任务与不同会话不串线",
        ],
    }
