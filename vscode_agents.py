"""Known editor extensions and display routes; never read extension settings."""
from __future__ import annotations

from pathlib import Path

ROUTES = {
    "openai.chatgpt": ("Codex", "codex", ".codex/config.toml", ".codex/AGENTS.md"),
    "anthropic.claude-code": ("Claude Code", "claude", ".claude.json", ".claude/CLAUDE.md"),
    "harcochen.dsh-vsc-integration": ("DSH", "dsh", ".dsh/profiles/web/cordis.patch.yml", ".dsh/AGENTS.md"),
    "codebuddyai.codebuddy-ai": ("CodeBuddy", "custom", "", ""),
    "github.copilot-chat": ("GitHub Copilot", "vscode", "AppData/Roaming/Code/User/mcp.json", ""),
}


def route_for(identity: str) -> tuple | None:
    return next((value for value in ROUTES.values() if value[0] == identity), None)


def discover(home: Path) -> list[dict]:
    """Read only bounded manifests in known stable/Insiders extension roots.

    Installed directories are evidence of installation, not enabled extensions.
    Deduplicate leftover versions and never execute extension code or the CLI.
    """
    from agent_discovery import read_json, magpie_state
    result = {}
    for relative, software in ((".vscode/extensions", "VS Code"),
                               (".vscode-insiders/extensions", "VS Code Insiders")):
        root = home / relative
        if not root.is_dir():
            continue
        # Narrow name globs, not a whole-disk or workspace search.
        for extension_id, (identity, backend, config, rules) in ROUTES.items():
            candidates = sorted(root.glob(extension_id + "-*"))[:32]
            found = []
            for folder in candidates:
                try:
                    manifest = read_json(folder / "package.json")
                    if (manifest.get("publisher", "").casefold() + "." +
                            manifest.get("name", "").casefold()) != extension_id:
                        continue
                    found.append(str(folder / "package.json"))
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
            if not found:
                continue
            manager = magpie_state(home, backend)
            result[(software, identity)] = {
                "id": software.lower().replace(" ", "-") + "-" + extension_id,
                "label": software + " · " + identity, "identity": identity,
                "software": software, "backend": backend, "mode": "guided",
                "detected": True, "location": str(home),
                "config_path": str(home / config) if config else str(root),
                "rules_path": str(home / rules) if rules else "",
                "extension_id": extension_id, "configuration": "not_verified",
                "manager": "magpie" if manager["managed"] else "nijika",
                "status": "发现具体扩展",
                "evidence": ["扩展清单匹配：" + extension_id,
                             "已安装不代表已启用；配置可能与命令行/后端共用"],
                "issue": "管理器配置无法核对。" if manager["error"] else "",
                "verification": "按此扩展生成接入与来源规则；需要在编辑器内实际调用验证。",
            }
    return list(result.values())


def instructions(identity: str, software: str) -> str:
    """Safe shared-backend rule: explicit metadata applies only to editor calls."""
    import json
    return (
        "【编辑器来源规则】\n"
        f"仅当当前任务确实运行在 {software} 的 {identity} 扩展中，"
        "调用虹夏 show_completion/request_decision 时必须增加 "
        f"agent_name={json.dumps(identity, ensure_ascii=False)}、"
        f"software={json.dumps(software, ensure_ascii=False)}。task 仅写任务名。\n"
        "此规则与命令行/桌面端共用时必须保留上述条件，其他宿主不得照搬 VS Code 标签。"
        "复用已有虹夏 MCP，不为区分编辑器重复添加同程序服务；"
        "不要把共享配置中的 NIJIKA_HOST_NAME 全局改成 VS Code。"
        "若工具不含来源参数，先报告需要更新/重载虹夏 MCP，不能假称来源已正确。\n"
    )
