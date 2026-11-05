"""Reviewed, backup-first adapters for local Agent notification clients."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import tomllib
import uuid
from pathlib import Path

from app_layout import bundled_mcp_path, validate_bundled_mcp
from control_store import ControlStore, IDENTIFIER
from notice_source import resolve_source
from notification_capabilities import notification_capability
from setup_config import (
    codex_service_update,
    json_service_update,
    remove_legacy_dsh_nijika_entry,
    repair_orphan_dsh_marker,
)
from agent_discovery import CLIENTS, CANONICAL_NAMES, JSON_CLIENTS, client_home, json_paths, bounded_bytes, parse_json, magpie_state, scan
from vscode_agents import instructions as vscode_instructions, route_for

CANONICAL_AGENT_NAMES = CANONICAL_NAMES
CLIENT_CAPABILITIES = {
    "codex": {"transport": "stdio MCP + 本机技能", "approval": "可选原生钩子，需本人信任",
              "completion": "MCP 主动调用；可选 Stop 兜底", "reload": "重载连接或新建任务；钩子另行审阅",
              "note": "不改原生审批权限；桌宠点击不能批准命令。"},
    "work": {"transport": "本机插件 + stdio MCP", "approval": "未接原生权限事件",
             "completion": "依靠 Agent 主动调用 MCP", "reload": "安装并启用插件后，新建本机 Work 任务",
             "note": "当前启动器需要 Codex CLI 与 python.exe；不适用于云端 Work。"},
    "dsh": {"transport": "desktop/web 配置 + stdio MCP", "approval": "未接原生权限事件",
            "completion": "MCP 主动调用 + 实时会话事件转接", "reload": "重启 DSH 并新建会话后验收事件",
            "note": "需检查两个 profile；晚到回复不会自动唤醒已结束的任务。"},
    "custom": {"transport": "通用 stdio MCP 配置导出", "approval": "取决于宿主专属集成",
               "completion": "依靠 Agent 主动调用 MCP", "reload": "由接收方 AI 核实客户端和配置作用域",
               "note": "Claude Code 可参考接入手册；不能向普通网页聊天安装本机服务。"},
}
for _client in JSON_CLIENTS:
    CLIENT_CAPABILITIES[_client] = {
        "transport": "用户级 JSON + 持久提醒规则", "approval": "本向导不安装原生权限钩子",
        "completion": "依靠 Agent 主动调用 MCP", "reload": "重载客户端或新建任务后实际调用",
        "note": "项目配置可能覆盖用户配置；找到文件不等于客户端已加载。"}
for _client, _capability in CLIENT_CAPABILITIES.items():
    _capability["reliability"] = notification_capability(_client)

INSTALL_RULES = """虹夏桌面提醒规则：
1. 实质成果太长、需要用户审阅时，调用 show_completion(task=30字内标题, summary=1–120字结果)，只发送一次；它只是通知，不是批准。即使只回答一句话或用户要求返回 JSON 也要提醒，JSON 原文改用安全摘要；只有内部标题生成、Codex 私有 helper/环境建议等明确后台任务、显式子任务或缺少有效轮次状态时保持安静。
2. 简单选择或能完整放进气泡的短成果审阅，使用 request_decision(task=30字内标题, question=80字内且至多3段的完整正文, options=2–3项)。
   每项必须含 label（不超过20显示列，约10个汉字）和 description（6–48字的一句影响说明）；最多一个 recommended=true，并在说明中解释理由。不能只写“方案A/方案B”。
3. 用同一个 request_id 调用 wait_for_reply(timeout_seconds=45)，pending 时继续等待，最多12轮。
   pending 只表示已排队，不能声称已显示或获准；不要重复发送同一问题，dismissed 也不是批准。
4. 收到 answered 后，在原聊天明确复述所选项再继续，无需再次确认。会话中断时保留原 ID，恢复后先 get_reply；较晚点击不会自动唤醒已结束的任务，只有这时才需用户回原会话说“继续”。
5. status=invalid 时按错误修正并重试一次；读取技能失败不等于工具不可用。工具确实不可用或修正后仍失败时，如实报告并在聊天沟通。
6. 在每轮最终回复前主动执行第1–2条检查，不能故意依赖 Codex Stop 兜底；兜底只会生成截断摘要。正常配置已提供 Agent/软件来源，默认省略可选 agent_name/software；DSH、WorkBuddy 等多模型宿主尤其不能把 Codex/宿主产品名当模型名。
7. 以客户端实际暴露的工具名称为准（可能带 nijika_pet/nijika_work_pet 前缀），四个功能是 show_completion、request_decision、wait_for_reply、get_reply。气泡点击不代替客户端命令授权，不授予或绕过权限；注册 MCP 不等于已接通原生审批/完成事件钩子。
8. 所有客户端共用通知核心和生命周期协议；单次 MCP 调用、读取 skill 或配置写入均不能证明每轮自动补发。必须分别报告主动调用验证与真实结束事件验证；不得让模型伪造 session_id/turn_id 或执行模拟事件冒充宿主验收。
"""

GUIDES = {
    "codex": {
        "title": "接下来请照这 4 步做",
        "steps": [
            "重启 Codex 或新开一个任务，让刚写入的 MCP 配置和技能生效（已打开的旧任务不会自动刷新）。",
            "把下面这段示例提示词粘贴到 Codex 新任务里发送，做第一次验证。",
            "如果第一次弹出 MCP 工具授权，选择允许；任务结束或需要你选择时，桌面虹夏会弹出气泡。",
            "没有气泡时先确认桌面虹夏正在运行，再回设置中心点一次“测试提醒”对比。",
        ],
        "prompt": "这个任务结束时，请用虹夏桌宠的 show_completion 给我发一条桌面完成提醒，标题写任务名，summary 写一句话结果。"
                  "如果中途需要我在两个方案里做选择，请改用 request_decision，每个选项写清楚名称和一句说明，然后等我点击。"
                  "现在先调用一次工具让我确认链路是否通。",
        "tip": "持久规则让新任务知道每轮都要提醒，无需每轮重复粘贴；仅注册 MCP 不保证每次都会主动调用，Codex 的 Stop 兜底会补发漏掉的轮次提醒。命令审批与完成兜底另需四项原生钩子，且须本人审阅信任。",
    },
    "work": {
        "title": "接下来请照这 4 步做",
        "steps": [
            "重启 ChatGPT 桌面客户端，让本机 Work 插件重新加载。",
            "打开一个在本机运行的 Work 新任务（云端 Work 不能运行本机程序）。",
            "确认工具列表里能看到虹夏，然后粘贴下面的示例提示词发送。",
            "选择时由 Agent 等待并读回桌面点击，直接继续；只有任务已经结束后才需回原聊天说“继续”。",
        ],
        "prompt": "这个任务结束时，请调用虹夏桌宠的 show_completion 给我发一条桌面完成提醒。"
                  "如果需要我在两个方案里选择，请调用 request_decision，每个选项写一句说明，然后等我桌面点击后再继续。",
        "tip": "仅限具备本机执行能力的 Work；首次接入后按客户端要求重载。普通决策通过 MCP，当前没有 Work 原生审批或完成兜底桥接。",
    },
    "dsh": {
        "title": "接下来请照这 4 步做",
        "steps": [
            "重启 DeepSeek Harness 桌面客户端，让新的 MCP 配置生效。",
            "新建一个会话（旧会话不会自动加载新配置）。",
            "把下面的示例提示词粘贴进去发送，确认虹夏工具可被调用。",
            "桌面出现气泡后点击选项；如果点击较晚，回到该会话继续说“我回复了”即可读取结果。",
        ],
        "prompt": "这个任务结束时，请调用虹夏桌宠的 show_completion 发一条桌面完成提醒；"
                  "需要我在多个方案里选择时，请用 request_decision 写清每个选项的名称和一句说明，然后等待我点击。",
        "tip": "正常等待中的点击会直接回传；仅已结束的会话需说“我回复了”再读回。完成事件转接需新会话验收；当前未接 DSH 原生审批。",
    },
    "custom": {
        "title": "复制给 AI，自动完成配置",
        "steps": [
            "软件会把接入文件保存到下方显示的本机目录，无需另行下载。",
            "点击“复制自动配置提示词”，粘贴给同一电脑上能读写文件、执行操作的 AI 客户端并发送。",
            "AI 按提示词检测自身客户端、备份并合并配置与提醒规则；如需重载或本人确认，由它告知。",
        ],
        "prompt": "接入虹夏 MCP 服务后，请用客户端实际暴露的工具。任务结束时用 show_completion 发桌面完成提醒；"
                  "需要我在方案间选择时用 request_decision，给出每个选项的名称和一句说明，等待我点击后再继续。",
        "tip": "普通网页聊天无法读写本机文件；请发给能操作本机文件的 AI。生成文件不代表客户端已连接。",
    },
}


def client_guide(client: str) -> dict:
    """Return the operator-facing steps and a copy-paste prompt for one client."""
    return GUIDES.get(client, GUIDES["custom"])


def client_files(client: str, mcp: Path, directory: Path, bundle: Path,
                 data_root: Path, application_root: Path | None = None) -> list[dict]:
    """List the concrete files each client needs, with absolute paths.

    ``exists`` is measured on the current machine so the settings window can show
    which pieces are already in place and which the user still has to create.
    """
    skill = directory / "skills" / "nijika-desktop-dialog" / "SKILL.md"
    root = application_root or mcp.parent.parent
    entries = [
        {"label": "虹夏 MCP 程序（所有客户端共用）", "path": str(mcp), "kind": "程序", "required": True},
        {"label": "已保存的 MCP 配置", "path": str(bundle / "nijika-mcp.json"),
         "kind": "接入文件", "required": True},
        {"label": "已保存的主动提醒规则", "path": str(bundle / "nijika-agent-instructions.txt"),
         "kind": "接入文件", "required": True},
        {"label": "自动配置提示词（可整份发给 AI）", "path": str(bundle / "nijika-setup-prompt.txt"),
         "kind": "提示词", "required": True},
        {"label": "通知能力与验收清单", "path": str(bundle / "nijika-notification-capabilities.json"),
         "kind": "能力清单", "required": True},
        {"label": "可供客户端安装的交互技能", "path": str(bundle / "SKILL.md"),
         "kind": "技能副本", "required": False},
        {"label": "接入手册（含手动接入说明）", "path": str(root / "AGENT_SETUP.md"),
         "kind": "文档", "required": False},
    ]
    if client == "codex":
        entries += [
            {"label": "Codex 配置（写入 MCP 服务）", "path": str(directory / "config.toml"), "kind": "配置", "required": True},
            {"label": "Codex 主动提醒规则", "path": str(directory / "AGENTS.md"), "kind": "规则", "required": True},
            {"label": "桌面交互技能", "path": str(skill), "kind": "技能", "required": False},
            {"label": "可选：Codex 原生通知钩子", "path": str(directory / "hooks.json"), "kind": "可选配置", "required": False},
            {"label": "可选：四事件钩子安装脚本", "path": str(root / "integrations/codex/install-hooks.ps1"), "kind": "可选脚本", "required": False},
            {"label": "可选：原生通知程序", "path": str(root / "dist/虹夏审批提醒.exe"), "kind": "可选程序", "required": False},
        ]
    elif client == "dsh":
        entries += [
            {"label": "DSH 实时事件转接模块", "path": str(root / "integrations/dsh/lifecycle-bridge.mjs"),
             "kind": "事件模块", "required": False},
            {"label": "统一生命周期程序", "path": str(root / "dist/虹夏审批提醒.exe"),
             "kind": "事件程序", "required": False},
            {"label": "DSH desktop 配置", "path": str(directory / "profiles" / "desktop" / "cordis.patch.yml"),
             "kind": "配置", "required": True},
            {"label": "DSH web 配置", "path": str(directory / "profiles" / "web" / "cordis.patch.yml"),
             "kind": "配置", "required": True},
            {"label": "DSH 主动提醒规则", "path": str(directory / "AGENTS.md"), "kind": "规则", "required": True},
            {"label": "桌面交互技能", "path": str(directory / "skills" / "nijika-dsh-dialog" / "SKILL.md"),
             "kind": "技能", "required": False},
        ]
    elif client in JSON_CLIENTS:
        config, rules = json_paths(client, directory)
        entries += [
            {"label": CLIENTS[client] + " 用户级 MCP 配置", "path": str(config), "kind": "配置", "required": True},
            {"label": CLIENTS[client] + " 主动提醒规则", "path": str(rules), "kind": "规则", "required": True},
        ]
    elif client == "work":
        staging = data_root / "integrations" / "work"
        entries += [
            {"label": "Work 插件市场清单", "path": str(staging / ".agents" / "plugins" / "marketplace.json"),
             "kind": "插件", "required": True},
            {"label": "Work 插件定义", "path": str(staging / "plugins" / "nijika-work-local" / "plugin.json"),
             "kind": "插件", "required": True},
            {"label": "Work MCP 启动配置", "path": str(staging / "plugins" / "nijika-work-local" / "mcp.json"),
             "kind": "配置", "required": True},
            {"label": "Work 桌面交互技能", "path": str(staging / "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md"),
             "kind": "技能", "required": True},
        ]
    for entry in entries:
        target = Path(entry["path"])
        entry["exists"] = target.is_file() if target.is_absolute() else False
    return entries


def marked_block(original: str, block: str, start: str, end: str) -> str:
    first, last = original.find(start), original.find(end)
    if (original.count(start) > 1 or original.count(end) > 1
            or (first >= 0) != (last >= 0) or (first >= 0 and last < first)):
        raise ValueError("原配置的虹夏标记不完整，请先检查该文件。")
    if first >= 0:
        return original[:first] + block.rstrip() + original[last + len(end):]
    return original.rstrip("\r\n") + "\n\n" + block.rstrip() + "\n"


def dsh_lifecycle_block(root: Path) -> str:
    for relative in ("integrations/dsh/lifecycle-bridge.mjs", "dist/虹夏审批提醒.exe"):
        if not (root / relative).is_file():
            raise ValueError("缺少 DSH 实时事件组件，请使用完整新版安装包：" + relative)
    plugin = (root / "integrations/dsh/lifecycle-bridge.mjs").resolve().as_uri().replace("'", "''")
    executable = str(root / "dist/虹夏审批提醒.exe").replace("'", "''")
    return ("# BEGIN NIJIKA-DSH-LIFECYCLE\n- insert:\n"
            "    - id: nijika-lifecycle-bridge\n"
            f"      name: '{plugin}'\n      config:\n        executable: '{executable}'\n"
            "# END NIJIKA-DSH-LIFECYCLE")


def normalize_codex_agent_name(original: str, agent_name: str) -> str:
    return normalize_codex_environment(original, {"NIJIKA_AGENT_NAME": agent_name})


def normalize_codex_environment(original: str, environment: dict[str, str]) -> str:
    """Update just the managed env, including table and inline TOML layouts."""
    expected = tomllib.loads(original)
    expected["mcp_servers"]["nijika-pet"].setdefault("env", {}).update(environment)
    lines = original.splitlines(keepends=True)
    section = ""
    found = set()
    env_header = None
    for index, line in enumerate(lines):
        match = re.match(r"^\[([^\]]+)\]\s*(?:#.*)?$", line.rstrip("\r\n"))
        if match:
            section = match.group(1)
            if section == "mcp_servers.nijika-pet.env":
                env_header = index
        if section == "mcp_servers.nijika-pet":
            inline = re.match(r"^(\s*env\s*=\s*\{)(.*?)(\}\s*(?:#.*)?)$", line.rstrip("\r\n"))
            if inline:
                body = inline.group(2)
                for key, value in environment.items():
                    replacement = json.dumps(value, ensure_ascii=False)
                    body, count = re.subn(
                        r"(" + re.escape(key) + r"\s*=\s*)(\"[^\"]*\"|'[^']*')",
                        lambda m: m[1] + replacement, body)
                    if not count:
                        body = body.rstrip().rstrip(",") + (", " if body.strip() else "") + key + " = " + replacement
                    found.add(key)
                newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                lines[index] = inline[1] + body + inline[3] + newline
        elif section == "mcp_servers.nijika-pet.env":
            for key, value in environment.items():
                updated, count = re.subn(
                    r"^(\s*" + re.escape(key) + r"\s*=\s*)(\"[^\"]*\"|'[^']*')",
                    lambda m: m[1] + json.dumps(value, ensure_ascii=False), lines[index])
                if count:
                    found.add(key)
                    lines[index] = updated
    missing = [f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
               for key, value in environment.items() if key not in found]
    if missing:
        if env_header is not None:
            if not lines[env_header].endswith("\n"):
                lines[env_header] += "\n"
            lines[env_header + 1:env_header + 1] = missing
        else:
            lines += ["\n[mcp_servers.nijika-pet.env]\n", *missing]
    result = "".join(lines)
    if tomllib.loads(result) != expected:
        raise ValueError("Codex env 格式不受支持，请人工核对；没有写入。")
    return result


def digest(data: bytes | None) -> str:
    return hashlib.sha256(data).hexdigest() if data is not None else "absent"


class AgentSetup:
    def __init__(self, root: Path, store: ControlStore, home: Path | None = None):
        self.root, self.store = root, store
        self.home = (home or Path.home()).resolve()
        self.use_environment = home is None
        self.mcp = bundled_mcp_path(root)
        self.plans: dict[str, dict] = {}
        self.batches: dict[str, dict] = {}
        self.lock = threading.Lock()

    def default_home(self, client: str) -> Path:
        return client_home(client, self.home, self.use_environment)

    def discover(self) -> dict:
        return {"clients": scan(self.home, self.mcp, use_environment=self.use_environment),
                "scanned_at": int(time.time()),
                "scope": "当前用户目录" if self.use_environment else "隔离测试目录（不是当前电脑的完整配置）",
                "note": "仅解析已知接入配置并返回安全摘要，不收集密钥、聊天内容或登录状态。"}

    def batch_plan(self, selected: list[str]) -> dict:
        if (not isinstance(selected, list) or not 1 <= len(selected) <= len(CLIENTS) - 1 or
                any(not isinstance(item, str) or item not in CLIENTS or item == "custom" for item in selected) or
                len(set(selected)) != len(selected)):
            raise ValueError("请选择不重复的受支持客户端。")
        if {"codex", "work"} <= set(selected):
            raise ValueError(
                "Codex 与 ChatGPT Work 共用本机 Codex 环境，请只选择一种接入方式；"
                "同时配置会生成两套 MCP 和重复提醒。"
            )
        results = []
        for client in selected:
            try:
                results.append({"client": client, "status": "ready",
                                "plan": self.plan(client, CLIENTS[client])})
            except (ValueError, OSError):
                results.append({"client": client, "status": "blocked",
                                "error": "无法安全预览。请用单独向导核对配置格式、同名服务或依赖；原配置未修改。"})
        batch_id = uuid.uuid4().hex
        self.batches = {key: value for key, value in self.batches.items()
                        if time.monotonic() - value["created"] < 600}
        if len(self.batches) >= 8:
            self.batches.pop(next(iter(self.batches)))
        self.batches[batch_id] = {"created": time.monotonic(), "results": results}
        return {"batch_id": batch_id, "results": results,
                "note": "按客户端分别应用；某项失败不回滚其他已成功项。Work 可能执行插件注册。"}

    def batch_apply(self, batch_id: str) -> dict:
        with self.lock:
            batch = self.batches.pop(batch_id, None)
        if not batch or time.monotonic() - batch["created"] > 600:
            raise ValueError("批量预览已过期或已应用，请重新扫描。")
        results = []
        for item in batch["results"]:
            if item["status"] != "ready":
                results.append(item)
                continue
            try:
                result = self.apply(item["plan"]["plan_id"])
                results.append({"client": item["client"], "status": result["agent"]["status"],
                                "agent_id": result["agent"]["id"], "backup_count": result["backup_count"]})
            except (ValueError, OSError):
                results.append({"client": item["client"], "status": "failed",
                                "error": "未完成，请重新扫描并用单独向导核对；若为 Work 请检查插件注册状态后再试。"})
        return {"results": results}

    def clients(self) -> list[dict]:
        result = []
        for client, label in CLIENTS.items():
            directory = self.default_home(client)
            if client in JSON_CLIENTS:
                present = json_paths(client, directory)[0].is_file() or bool(shutil.which(client))
            else:
                present = ((directory / "config.toml").is_file() or bool(shutil.which("codex"))) if client in ("codex", "work") else directory.is_dir()
            result.append({"id": client, "label": label, "detected": bool(present) if client != "custom" else True,
                           "location": str(directory) if client != "custom" else "",
                           "capabilities": CLIENT_CAPABILITIES[client]})
        return result

    def export(self, name: str, agent_name: str | None = None, software: str = "") -> dict:
        source = resolve_source("auto" if agent_name else name[:20], software, agent_name=agent_name)
        environment = {"NIJIKA_AGENT_NAME": source.agent}
        if source.software != "未识别软件":
            environment["NIJIKA_HOST_NAME"] = source.software
        return {"mcpServers": {"nijika-pet": {"command": str(self.mcp), "args": [],
                "env": environment}}}

    def export_agent(self, agent: dict) -> dict:
        # Built-in clients are stable even for old profiles with a custom nickname.
        source = CANONICAL_AGENT_NAMES.get(agent["client"], agent["source_name"])
        result = (self.export(source) if agent["client"] in CANONICAL_AGENT_NAMES else
                  self.export(source, agent.get("agent_identity"), agent.get("software", "")))
        server = result["mcpServers"]["nijika-pet"]
        server["env"]["NIJIKA_PROFILE_ID"] = agent["id"]
        if agent["client"] == "copilot":
            server.update(type="local", tools=["*"])
        return result

    def bundle_directory(self, agent_id: str) -> Path:
        if not isinstance(agent_id, str) or not IDENTIFIER.fullmatch(agent_id):
            raise ValueError("Agent 档案编号无效。")
        return (self.store.root / "integrations" / "agents" / agent_id).resolve()

    def describe(self, agent: dict) -> dict:
        """Build a self-contained setup prompt without writing on state polls."""
        client = agent["client"]
        directory = Path(agent["location"])
        bundle = self.bundle_directory(agent["id"])
        config = self.export_agent(agent)
        files = client_files(client, self.mcp, directory, bundle, self.store.root, self.root)
        editor = (client == "custom" and
                  str(agent.get("software", "")).casefold() in {"vs code", "vs code insiders"})
        route = route_for(agent.get("agent_identity", "")) if editor else None
        if route:
            for label, relative in (("扩展后端配置（可能与其他宿主共用）", route[2]),
                                    ("扩展后端持久规则（须附编辑器条件）", route[3])):
                if relative:
                    path = directory / relative
                    files.append({"label": label, "path": str(path), "kind": "配置参考",
                                  "required": False, "exists": path.is_file()})
        guide = {**client_guide(client), "steps": list(client_guide(client)["steps"])}
        reliability = notification_capability(client)
        config_text = json.dumps(config, ensure_ascii=False, indent=2)
        paths = "\n".join(item["label"] + "：" + item["path"] for item in files)
        capabilities = {
            "codex": "普通完成提醒与选择通过 MCP。可选的命令审批提醒/完成兜底需要原生钩子，"
                     "不是仅添加 MCP 就具备；钩子目标、安装脚本和程序路径已列在清单。"
                     "只有用户已要求这些原生提醒时，才在既有授权范围内核对或补装：脚本参数 "
                     "CodexHome 指向上述 Codex 配置目录，ApprovalExe 指向上述原生通知程序。"
                     "核对 UserPromptSubmit、PermissionRequest、PostToolUse、Stop 四项，保留其他钩子及 Computer Use 的 notify。"
                     "新增或改变的钩子需本人在 /hooks 审阅信任；旧两项审批已信任不代表新增的两项也可信任。"
                     "不代写信任、不使用信任或权限跳过参数。未要求原生提醒时只报告这个可选项，不自动安装。",
            "work": "本机 Work 使用插件中的 nijika-work-pet 服务和配套技能；不要将通用 nijika-pet JSON "
                    "覆盖 Work 的插件清单。当前只验证 MCP 普通通知/选择，尚未实现 Work 原生审批或完成事件兜底。"
                    "正常等待的桌面点击应直接继续任务；已结束的任务不能被一次较晚点击独立唤醒。",
            "dsh": "DSH 的 desktop/web 两个配置均需核对。当前 MCP 支持普通完成提醒、决策与回执，"
                   "尚未实现 DSH 宿主原生权限自动桥接；完成事件使用本项目实时会话转接模块，"
                   "由同一通知核心处理，接口核对版本为 0.2.1-rc.2 / 0.2.1-rc.3，需重载后真实验收；不要把 Codex 的钩子安装到 DSH。"
                   "Agent 等待时直接读回点击；只有已结束的会话才需用户说“继续”或“我回复了”。",
            "custom": "通用 stdio MCP 配置只提供普通提醒/决策能力；原生权限和完成兜底取决于实际客户端的独立集成，不能承诺全平台已接通。"
                      "Claude Code 目前不在向导专属选项中，可按其他 MCP 客户端检测自身格式；其专属手动接入见上述接入手册 AGENT_SETUP.md。",
        }
        adapters = {
            "codex": "目标为 Codex。将 nijika-pet 服务按 TOML 格式合并进上述 config.toml；"
                     "将规则合并到上述 AGENTS.md，技能可从接入目录的 SKILL.md 安装。保持已有服务权限不变。",
            "work": "目标为本机 Work。核对上述插件清单与 mcp.json 中的 MCP 程序路径。"
                    "使用客户端提供的本机插件安装/启用入口；若须重启桌面客户端，只在完成配置后说明。"
                    "不要把通用 JSON 直接覆盖插件清单；Work 提醒规则随插件技能加载。",
            "dsh": "目标为 DSH。按客户端实际支持的结构合并 desktop/web 的 cordis.patch.yml 中"
                   "虹夏 stdio 服务及其环境变量；规则写入上述 AGENTS.md。保留其他 patch，不重复添加。"
                   "通过本项目 integrations/dsh/install.ps1 安装独立标记的实时事件模块；"
                   "已经由向导添加时只核对，不重复安装，不修改其他模块或原生权限。",
            "custom": "请先识别你当前实际运行的 AI 客户端和配置作用域，核实它的 MCP 配置文件与"
                      "持久规则文件路径（通过本机设置或官方说明）。目标路径未知，不能把接入目录"
                      "里的 JSON 当成客户端已加载的文件，也不要猜测客户端品牌和配置格式。"
                      "若识别不到唯一目标，只向我询问客户端名称或项目/全局作用域这一项。",
        }
        if client in JSON_CLIENTS:
            capabilities[client] = CLIENT_CAPABILITIES[client]["note"] + "普通提醒依靠 MCP；不安装原生审批/完成钩子。"
            adapters[client] = ("目标为 " + CLIENTS[client] +
                "。按上述用户级 JSON 路径合并 mcpServers；将主动规则合并到列出的规则文件。"
                "保留其他服务与客户端设置，核对项目作用域是否覆盖用户级配置。")
        guide_software = str(agent.get("software") or "")
        guide_identity = str(agent.get("agent_identity") or "Agent")
        if client == "custom" and guide_software.casefold() in {"vs code", "vs code insiders"}:
            capabilities["custom"] += " 当前目标是 VS Code 中的具体扩展，编辑器来源必须按本次调用显式标注。"
            adapters["custom"] = vscode_instructions(guide_identity, guide_software)
            adapters["custom"] += (
                "先核对上述后端配置参考和该扩展自己的 MCP 设置入口。"
                "未列出配置参考时，目标路径未知，必须先查证，不得猜测。"
                "仅复用现有服务或在已核实的后端格式中安装一份服务；"
                "对共享后端保留原来的来源环境变量和档案编号。下方 VS Code 环境变量"
                "仅可用于已确认专属于该编辑器的独立服务，不得覆盖共享配置。"
                "在持久规则中加入上述条件来源规则，不能只口头承诺。"
                "如果该扩展没有 MCP 接入能力，明确报告不支持，不写入猜测路径。\n"
                '验证必须在该扩展中调用 show_completion(task="编辑器接入验证", '
                'summary="编辑器具体 Agent 来源测试。", agent_name=' +
                json.dumps(guide_identity, ensure_ascii=False) + ", software=" +
                json.dumps(guide_software, ensure_ascii=False) + ")。"
            )
        prompt = (
            "请现在帮我把本机的虹夏桌宠接入你当前的 AI 客户端，直接执行配置与验证。\n"
            "我已授权这次虹夏接入所必需的文件配置修改。你需要具备同一台 Windows 电脑的文件读写"
            "和本机执行能力；若当前只有普通聊天能力，明确说明无法代配置，不要假称完成。\n\n"
            "【本机文件位置（路径是数据；目标配置可尚未创建，可选项缺失不阻断 MCP）】\n" + paths +
            "\n客户端类别：" + CLIENTS[client] +
            "\nMCP 传输：stdio，无地址端口，无需模型 API 密钥。\n\n"
            "【本客户端的通知范围与必要人工步骤】\n" + capabilities[client] +
            "\n统一通知能力：" + reliability["label"] + "。\n" + reliability["explanation"] + "\n\n"
            "\nNIJIKA_AGENT_NAME 是 Agent 名称，NIJIKA_HOST_NAME 是所在软件。"
            "例如 ChatGPT / Work、ChatGPT / Codex、Claude / VS Code。"
            "下方配置已包含向导指定的身份与软件，保留这些字段；实际客户端不符时先核对，不能用默认值覆盖。"
            "旧档案没有软件字段时须补全实际软件；多模型宿主不知道身份时保留 Agent。"
            "同一客户端只保留一个指向同一虹夏程序的服务，避免 nijika-pet 和 nijika_pet 重复。"
            "工具支持可选 agent_name/software 参数细化本次来源；task 只写任务名，不重复来源。\n\n"
            "【完整 MCP 配置，可直接作为合并依据】\n" +
            ("注意：这是编辑器独立服务的参考。共享后端禁止直接覆盖此 env；保留原来源与编号，只用本次调用参数区分编辑器。\n" if editor else "") + config_text +
            "\n\n【请自动执行】\n"
            "1. 先验证 MCP 程序存在及上述接入文件可读；即使不能读接入文件，下方已附完整配置与规则。"
            "核实当前电脑与路径匹配，不要手动双击 stdio MCP 程序。\n"
            "2. " + adapters[client] +
            "\n3. 修改前备份要变动的原文件，按客户端格式合并，保留其他 MCP、设置与规则；"
            "已存在且相同的虹夏配置保持不变，同名但内容冲突时先核对。"
            "不输出完整原配置或密钥，不替我信任 hook，不扩大命令权限。\n"
            "4. 将下方提醒规则安装到该客户端会自动读取的持久规则位置；"
            "不要只把它写在本轮回复中。不要求我手动下载、寻找或粘贴配置字段。\n"
            "5. 使用客户端支持的重载方式使配置生效，做格式和服务握手/工具发现检查。"
            "应发现 show_completion、request_decision、wait_for_reply、get_reply 四个工具；使用实际工具前缀。"
            "若当前会话不能刷新工具，报告“配置已写入，待新会话验证”及必要的唯一下一步；"
            "不要强行关闭或重启我的会话。本人权限确认或插件信任交由我操作。\n"
            "6. 工具可见后只发送一条 show_completion(task=\"虹夏接入验证\","
            " summary=\"当前 AI 客户端已发现虹夏工具；这是一条接入测试提醒。\")。"
            "文件存在、面板测试和 pending 均不证明外部客户端已连通或气泡已显示。"
            "主动调用测试和宿主结束事件必须分开验收；未接事件时明确报告“仅主动调用”，"
            "不要为了通过测试让模型伪造会话或轮次标识，不要安装其他客户端的钩子。"
            "最后列明实际改动的文件、备份位置、验证结果和未完成项。\n\n"
            "【需要安装的持久提醒规则】\n" + INSTALL_RULES +
            ("\n" + vscode_instructions(guide_identity, guide_software) if editor else "")
        )
        guide["prompt"] = prompt
        guide["title"] = "复制给 AI，自动完成配置"
        if client != "custom":
            guide["steps"] = [
                "软件已准备接入文件，准确保存位置见下方清单。",
                "复制下方自动配置提示词，发给这台电脑上能读写文件的 AI 客户端。",
                "AI 会按真实路径核对、补齐和验证；需要重载或本人确认时会明确告知。",
            ]
        if agent.get("manager") == "magpie":
            guide.update(title="由 MAGPIE 管理，核对现有连接",
                steps=["在 MAGPIE 核对虹夏仅分发一次到此客户端，并同步。",
                       "重载该客户端，复制下面的只读验证提示词给新任务。",
                       "共享连接不含本档案编号时，面板不会自动认领其调用；请在气泡核对来源和点击回传。"],
                prompt=("当前虹夏由 MAGPIE 管理。本次不授权修改客户端配置；不要新增服务或抢占管理权。"
                    "请只读核对现有虹夏工具，缺失时报告需在 MAGPIE 同步/重载，不能假称已连接。\n"
                    "预期气泡来源：" + self.export_agent(agent)["mcpServers"]["nijika-pet"]["env"]["NIJIKA_AGENT_NAME"] +
                    " · " + agent.get("software", "") + "。多模型宿主不知道 Agent 身份时保留 Agent。\n"
                    "工具可见后只调用一次 show_completion(task=\"虹夏接入验证\", summary=\"现有 MAGPIE 连接的工具调用测试。\")。"
                    "以实际工具前缀为准；支持来源参数时填写实际 agent_name/software。"
                    "pending 只表示排队，不等于已显示。不要输出原配置、环境变量或凭据。"),
                tip="切换为虹夏管理时，先在 MAGPIE 取消该目标分发，再重新扫描；不自动修改管理器。")
            if editor:
                guide["prompt"] += "\n" + vscode_instructions(guide_identity, guide_software)
                guide["prompt"] += "\n本次只验证来源参数；不安装或修改持久规则。"
        if agent.get("manager") == "magpie":
            reliability["explanation"] = (
                "当前由 MAGPIE 管理，本向导没有安装或更新结束事件模块；"
                "请由配置所有者核对独立事件接入。只有真实新轮次验证后才能确认启用。"
            )
            guide["prompt"] += ("\n统一通知能力：" + reliability["label"] + "。\n" +
                                reliability["explanation"] +
                                "本次只验证主动调用，不伪造事件标识或宣称自动补发通过。")
        guide["tip"] += " " + reliability["explanation"]
        return {"guide": guide, "needed_files": files, "export": config,
                "notification_capability": reliability,
                "bundle_directory": str(bundle),
                "bundle_ready": all((bundle / name).is_file() for name in
                                    ("nijika-mcp.json", "nijika-agent-instructions.txt", "nijika-setup-prompt.txt",
                                     "nijika-notification-capabilities.json"))}

    def prepare_files(self, agent: dict) -> dict:
        """Save durable per-agent handoff files; never modify an unknown client."""
        bundle = self.bundle_directory(agent["id"])
        bundle.mkdir(parents=True, exist_ok=True)
        info = self.describe(agent)
        contents = {
            "nijika-mcp.json": json.dumps(info["export"], ensure_ascii=False, indent=2) + "\n",
            "nijika-agent-instructions.txt": INSTALL_RULES,
            "nijika-setup-prompt.txt": info["guide"]["prompt"],
            "nijika-notification-capabilities.json": json.dumps(
                {"client": agent["client"], "mcp_executable": str(self.mcp),
                 "lifecycle_executable": str(self.root / "dist/虹夏审批提醒.exe"),
                 **info["notification_capability"]},
                ensure_ascii=False, indent=2,
            ) + "\n",
        }
        if agent["client"] == "custom" and agent.get("software", "").casefold() in {"vs code", "vs code insiders"}:
            contents["nijika-agent-instructions.txt"] += "\n" + vscode_instructions(
                agent.get("agent_identity") or "Agent", agent["software"])
        skill_path = {"dsh": "integrations/dsh/nijika-dsh-dialog/SKILL.md",
                      "work": "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md"}.get(
                          agent["client"], "skills/nijika-desktop-dialog/SKILL.md")
        skill = (self.root / skill_path).read_text(encoding="utf-8-sig")
        contents["SKILL.md"] = skill
        for name, content in contents.items():
            destination = bundle / name
            if destination.is_file() and destination.read_text(encoding="utf-8") == content:
                continue
            temporary = bundle / (name + "." + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_text(content, encoding="utf-8")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        return self.describe(agent)

    def _add_file(self, files: list, path: Path, content: str, purpose: str,
                  expected_digest: str | None = None) -> None:
        previous = path.read_bytes() if path.exists() else None
        if expected_digest is not None and digest(previous) != expected_digest:
            raise ValueError("读取配置期间文件已被其他程序修改，请重新预览；没有写入。")
        data = content.encode("utf-8")
        if previous != data:
            files.append({"path": path, "before": previous, "after": data, "purpose": purpose})

    def plan(self, client: str, name: str, location: str = "",
             agent_identity: str | None = None, software: str = "") -> dict:
        if client not in CLIENTS or not isinstance(name, str) or not 1 <= len(name.strip()) <= 30 or any(ord(c) < 32 for c in name):
            raise ValueError("请选择客户端，并填写 1–30 字的 Agent 名称。")
        validate_bundled_mcp(self.root)
        name = name.strip()
        directory = Path(location).expanduser() if location else self.default_home(client)
        if not directory.is_absolute():
            raise ValueError("配置目录需要填写完整的本机绝对路径。")
        directory = directory.resolve()
        if str(directory).startswith("\\\\"):
            raise ValueError("本轮只支持本机配置目录，不支持网络共享。")
        files, notes, commands = [], [], []
        source_name = CANONICAL_AGENT_NAMES.get(client, name)
        if client == "custom":
            if not isinstance(software, str) or not software.strip() or software.strip() in ("auto", "未识别软件"):
                raise ValueError("请填写实际所在软件，例如 VS Code 或 Obsidian。")
            source = resolve_source("auto", software, agent_name=agent_identity or "Agent")
        else:
            source = resolve_source(source_name)
        agent_identity, software = source.agent, source.software
        existing = next((item for item in self.store.agents() if item["client"] == client and
                         item["location"] == str(directory) and
                         (client != "custom" or (item.get("software") == software and
                                                item.get("agent_identity") == agent_identity))), None)
        agent_id = existing["id"] if existing else uuid.uuid4().hex
        manager_client = client
        if client == "custom":
            manager_client = {"workbuddy": "workbuddy", "workbuddy ai": "workbuddy-ai",
                "vs code": "vscode", "obsidian": "obsidian", "claude desktop": "claude-desktop"}.get(
                    software.casefold(), "custom")
            if software.casefold() in {"vs code", "vs code insiders"}:
                route = route_for(agent_identity)
                if route:
                    manager_client = route[1]
        manager = magpie_state(self.home, manager_client)
        if manager["error"]:
            raise ValueError("MAGPIE 配置无法安全读取，管理归属不明确；没有写入。")
        managed = manager["managed"]
        dsh_profiles: dict[str, tuple[Path, bytes, str]] = {}
        if client == "dsh":
            for profile in ("desktop", "web"):
                path = directory / "profiles" / profile / "cordis.patch.yml"
                if not path.is_file():
                    if managed:
                        continue
                    raise ValueError(f"没有找到 DSH {profile} 配置，请先启动 DSH 完成初始化或检查目录。")
                raw = bounded_bytes(path)
                original = raw.decode("utf-8-sig")
                dsh_profiles[profile] = (path, raw, repair_orphan_dsh_marker(original))
        environment = self.export(source_name, agent_identity, software)["mcpServers"]["nijika-pet"]["env"]
        environment["NIJIKA_PROFILE_ID"] = agent_id
        notes.append("预期气泡头部：" + source.heading + "；伙伴昵称只用于管理，任务名另起一行。")
        if managed:
            notes.append("检测到 MAGPIE 管理：只保存虹夏档案，不写客户端配置或执行注册。保持 MAGPIE 分发，重载后用宿主实际调用验证。")
            for profile, (path, raw, cleaned) in dsh_profiles.items():
                if cleaned != raw.decode("utf-8-sig"):
                    self._add_file(files, path, cleaned,
                                   f"清理 DSH {profile} 遗留的孤立虹夏标记，保留其他配置",
                                   digest(raw))
                    notes.append(f"检测到 DSH {profile} 的孤立虹夏开始标记；只移除该标记，不改 MAGPIE 服务。")
        elif client == "custom" and software.casefold() in {"vs code", "vs code insiders"}:
            route = route_for(agent_identity)
            if route and route[3]:
                path = directory / route[3]
                raw = bounded_bytes(path) if path.exists() else None
                original = raw.decode("utf-8-sig") if raw is not None else ""
                # One conditional editor block per engine; the backend MCP/env
                # remains untouched and CLI tasks do not inherit an editor label.
                marker = "NIJIKA-VSCODE-SOURCE" + ("-INSIDERS" if software == "VS Code Insiders" else "")
                block = ("# BEGIN " + marker + "\n" +
                         vscode_instructions(agent_identity, software) +
                         "# END " + marker)
                self._add_file(files, path, marked_block(original, block,
                    "# BEGIN " + marker, "# END " + marker),
                    "合并仅在 VS Code 任务生效的来源规则，保留共享 MCP 配置", digest(raw))
                notes.append("只安装条件来源规则；共享 MCP/权限不修改。需在此扩展实际发现工具并验证；缺服务时复制专属提示词补齐。")
            else:
                notes.append("此扩展的 MCP/持久规则格式仍需在其设置中核实；生成专属资料，不写猜测路径。")
        elif client in JSON_CLIENTS:
            path, rules = json_paths(client, directory)
            raw = bounded_bytes(path) if path.exists() else None
            document = parse_json(raw) if raw is not None else {}
            if client == "claude":
                projects = document.get("projects", {})
                if not isinstance(projects, dict):
                    raise ValueError("Claude 项目配置格式无法核对。")
                if any(isinstance(p, dict) and isinstance(p.get("mcpServers"), dict) and
                       any(key in ("nijika-pet", "nijika_pet") or
                           (isinstance(v, dict) and v.get("command") == str(self.mcp))
                           for key, v in p["mcpServers"].items()) for p in projects.values()):
                    raise ValueError("Claude 项目作用域存在虹夏服务，请先核对，避免覆盖用户级来源。")
            updated = json_service_update(document, self.mcp, environment, client, self.root)
            if document != updated:
                self._add_file(files, path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
                               "合并用户级 MCP，保留其他服务和设置", digest(raw))
            original = rules.read_text(encoding="utf-8-sig") if rules.exists() else ""
            self._add_file(files, rules, marked_block(original,
                "# BEGIN NIJIKA-DIALOG\n" + INSTALL_RULES + "# END NIJIKA-DIALOG",
                "# BEGIN NIJIKA-DIALOG", "# END NIJIKA-DIALOG"), "合并主动提醒规则")
            notes.append("重载客户端并新建任务；项目作用域可能覆盖用户级设置，不自动更改项目或命令权限。")
        elif client == "codex":
            path = directory / "config.toml"
            original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            try:
                config = tomllib.loads(original)
            except tomllib.TOMLDecodeError as error:
                raise ValueError("Codex 配置格式无效，请先修复 config.toml。") from error
            updated, migration_notes = codex_service_update(
                original, self.mcp, self.root,
                environment, normalize_codex_environment)
            notes.extend(migration_notes)
            if "nijika-pet" in tomllib.loads(updated).get("mcp_servers", {}):
                self._add_file(files, path, updated, "统一 Codex 虹夏来源标识并保留其他配置")
                notes.append("保留已有虹夏权限设置；来源为 ChatGPT · Codex，目标程序：" + str(self.mcp))
            else:
                block = ("# BEGIN NIJIKA-UI-MCP\n[mcp_servers.nijika-pet]\ncommand = " +
                         json.dumps(str(self.mcp), ensure_ascii=False) +
                         "\n[mcp_servers.nijika-pet.env]\n" +
                         "\n".join(key + " = " + json.dumps(value, ensure_ascii=False) for key, value in
                                   environment.items()) +
                         "\n# END NIJIKA-UI-MCP")
                updated = marked_block(original, block, "# BEGIN NIJIKA-UI-MCP", "# END NIJIKA-UI-MCP")
                tomllib.loads(updated)
                self._add_file(files, path, updated, "添加虹夏 MCP 服务，保留其他配置")
            self._add_file(files, directory / "skills/nijika-desktop-dialog/SKILL.md",
                           (self.root / "skills/nijika-desktop-dialog/SKILL.md").read_text(encoding="utf-8"), "安装桌面交互技能")
            instructions = (self.root / "distribution/codex-global-instructions.txt").read_text(encoding="utf-8-sig")
            path = directory / "AGENTS.md"
            original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            self._add_file(files, path, marked_block(original, instructions,
                           "# BEGIN NIJIKA-CODEX-DIALOG", "# END NIJIKA-CODEX-DIALOG"), "合并主动提醒规则")
            notes.append("新开 Codex 任务后生效；命令审批 hook 的本人信任仍需在客户端完成。")
        elif client == "dsh":
            for profile in ("desktop", "web"):
                path, raw, original = dsh_profiles[profile]
                if ("id: nijika-lifecycle-bridge" in original
                        and "# BEGIN NIJIKA-DSH-LIFECYCLE" not in original):
                    raise ValueError("DSH 中已有未受标记管理的事件模块，请先核对，避免重复。")
                if "id: mcp-nijika-pet" in original and "# BEGIN NIJIKA-DSH-MCP" not in original:
                    raise ValueError("DSH 中已有不受虹夏标记管理的同名条目，请先人工核对。")
                command = str(self.mcp).replace("'", "''")
                original = remove_legacy_dsh_nijika_entry(original)
                source = resolve_source(source_name)
                agent_name = source.agent.replace("'", "''")
                block = ("# BEGIN NIJIKA-DSH-MCP\n- insert:\n    - id: mcp-nijika-pet\n"
                         "      name: '@deepseek-ai/dsh-mcp-client'\n      config:\n"
                         "        serverName: nijika_pet\n        transport: stdio\n"
                         f"        command: '{command}'\n        env:\n          NIJIKA_AGENT_NAME: '{agent_name}'\n"
                         f"          NIJIKA_HOST_NAME: '{source.software}'\n"
                         f"          NIJIKA_PROFILE_ID: '{agent_id}'\n"
                         "# END NIJIKA-DSH-MCP")
                updated = marked_block(original, block, "# BEGIN NIJIKA-DSH-MCP", "# END NIJIKA-DSH-MCP")
                updated = marked_block(updated, dsh_lifecycle_block(self.root),
                                       "# BEGIN NIJIKA-DSH-LIFECYCLE", "# END NIJIKA-DSH-LIFECYCLE")
                self._add_file(files, path, updated, f"配置 DSH {profile} 的 MCP", digest(raw))
            self._add_file(files, directory / "skills/nijika-dsh-dialog/SKILL.md",
                           (self.root / "integrations/dsh/nijika-dsh-dialog/SKILL.md").read_text(encoding="utf-8"), "安装 DSH 桌宠交互技能")
            path = directory / "AGENTS.md"
            original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            instructions = (self.root / "integrations/dsh/global-instructions.txt").read_text(encoding="utf-8")
            self._add_file(files, path, marked_block(original, instructions, "# BEGIN NIJIKA-DSH-DIALOG", "# END NIJIKA-DSH-DIALOG"), "合并 DSH 主动提醒规则")
            notes.append("重启 DSH 并新建会话后测试；已结束的会话不能由 stdio MCP 独立唤醒。")
        elif client == "work":
            executable = shutil.which("codex")
            if not executable:
                raise ValueError("未检测到 Codex CLI；Work 本机插件安装需要该客户端工具。")
            if not shutil.which("python.exe"):
                raise ValueError("Work 插件当前需要 PATH 中可用的 python.exe。")
            staging = self.store.root / "integrations" / "work"
            sources = [".agents/plugins/marketplace.json", "plugins/nijika-work-local/plugin.json",
                       "plugins/nijika-work-local/mcp.json", "plugins/nijika-work-local/scripts/run_mcp.py",
                       "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md"]
            for relative in sources:
                content = (self.root / relative).read_text(encoding="utf-8")
                if relative.endswith("mcp.json"):
                    manifest = json.loads(content)
                    server = manifest["mcpServers"]["nijika-work-pet"]
                    server["args"][-1] = str(self.mcp)
                    server.setdefault("env", {}).update(environment)
                    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
                self._add_file(files, staging / relative, content, "准备本机 Work 插件文件")
            commands = [[executable, "plugin", "marketplace", "add", str(staging), "--json"],
                        [executable, "plugin", "add", "nijika-work-local@nijika-local", "--json"]]
            notes.append("将通过 Codex CLI 注册并安装本机插件；随后重启桌面客户端，在本机 Work 新任务中验证。")
        else:
            notes.append("将接入文件保存在本机专属目录。复制自动配置提示词给有本机操作能力的 AI，由它核实并接入自己的客户端。")
        plan_id = uuid.uuid4().hex
        self.plans = {key: value for key, value in self.plans.items() if time.monotonic() - value["created"] < 600}
        if len(self.plans) >= 32:
            self.plans.pop(next(iter(self.plans)))
        self.plans[plan_id] = {"client": client, "name": name, "source_name": source_name, "id": agent_id,
                              "agent_identity": agent_identity, "software": software,
                              "location": str(directory), "files": files, "notes": notes,
                              "commands": commands, "created": time.monotonic()}
        self.plans[plan_id]["manager"] = "magpie" if managed else "nijika"
        self.plans[plan_id]["manager_digest"] = manager["digest"]
        self.plans[plan_id]["manager_client"] = manager_client
        return {"plan_id": plan_id, "client": client, "name": name, "notes": notes,
                "manager": "magpie" if managed else "nijika",
                "files": [{"path": str(item["path"]), "purpose": item["purpose"],
                           "action": "更新并备份" if item["before"] is not None else "新建"} for item in files],
                "external_action": bool(commands), "export": self.export(source_name, agent_identity, software),
                "instructions": INSTALL_RULES,
                **self.describe(self.plans[plan_id])}

    def apply(self, plan_id: str) -> dict:
        with self.lock:
            plan = self.plans.get(plan_id)
            if not plan or time.monotonic() - plan["created"] > 600:
                raise ValueError("配置预览已过期，请重新检测。")
            if any(item["id"] != plan["id"] and item["client"] == plan["client"] and
                   item["location"] == plan["location"] and
                   (plan["client"] != "custom" or
                    (item.get("software") == plan["software"] and
                     item.get("agent_identity") == plan["agent_identity"]))
                   for item in self.store.agents()):
                raise ValueError("预览后已有同一客户端档案被添加，请重新预览，避免重复登记。")
            manager = magpie_state(self.home, plan["manager_client"])
            if manager["error"] or manager["digest"] != plan["manager_digest"]:
                raise ValueError("预览后 MAGPIE 管理配置发生变化，请重新扫描，避免两个管理器冲突。")
            for item in plan["files"]:
                path = item["path"]
                now = path.read_bytes() if path.exists() else None
                if digest(now) != digest(item["before"]):
                    raise ValueError("预览后配置文件已被其他程序修改，请重新检测，避免覆盖。")
            backups, completed = [], []
            try:
                for item in plan["files"]:
                    path = item["path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if item["before"] is not None:
                        backup = path.with_name(path.name + ".bak-nijika-" + uuid.uuid4().hex[:12])
                        backup.write_bytes(item["before"])
                        backups.append(str(backup))
                    temporary = path.with_name(path.name + ".tmp-nijika-" + uuid.uuid4().hex[:8])
                    try:
                        temporary.write_bytes(item["after"])
                        temporary.replace(path)
                    finally:
                        temporary.unlink(missing_ok=True)
                    completed.append(item)
            except OSError:
                for item in reversed(completed):
                    if item["before"] is None:
                        item["path"].unlink(missing_ok=True)
                    else:
                        item["path"].write_bytes(item["before"])
                raise
            for command in plan["commands"]:
                environment = {**os.environ, "CODEX_HOME": plan["location"]}
                try:
                    result = subprocess.run(command, env=environment, capture_output=True, timeout=60,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
                except subprocess.TimeoutExpired as error:
                    raise ValueError("Work 插件安装超时，可能已有部分操作完成；请先重新检测客户端，不要重复点击。") from error
                if result.returncode:
                    raise ValueError("Work 插件注册未完成；准备文件已保留，请检查客户端的插件状态后重新检测。")
            item = {"id": plan["id"], "name": plan["name"],
                    "source_name": plan["source_name"], "client": plan["client"], "location": plan["location"],
                    "agent_identity": plan["agent_identity"], "software": plan["software"],
                    "status": "managed" if plan["manager"] == "magpie" else "exported" if plan["client"] == "custom" else "configured",
                    "manager": plan["manager"],
                    "test_request_id": None, "updated_at": int(time.time()), "backups": backups}
            info = self.prepare_files(item)
            self.store.save_agent(item)
            self.plans.pop(plan_id, None)
            return {"agent": {**item, **info},
                    "notes": plan["notes"], "backup_count": len(backups)}
