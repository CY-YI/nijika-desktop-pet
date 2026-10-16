"""Reviewed, backup-first adapters for local Agent notification clients."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import tomllib
import uuid
from pathlib import Path

from control_store import ControlStore, IDENTIFIER

CLIENTS = {"codex": "Codex", "work": "ChatGPT Work", "dsh": "DeepSeek Harness", "custom": "其他 MCP 客户端"}

INSTALL_RULES = """虹夏桌面提醒规则：
1. 任务完成且需要用户审阅结果时，调用虹夏 MCP 的 show_completion(task=简短标题, summary=1–120字结果)，只发送一次。
2. 需要用户做简单选择时调用 request_decision(task=标题, question=足够作答的正文, options=选项列表)。
   每个选项必须含 label（约10个汉字以内）和 description（6–48字的一句影响说明）；最多一个 recommended=true 并解释推荐原因。
3. 用同一个 request_id 调用 wait_for_reply(timeout_seconds=45)，pending 时继续等待，最多12轮。
   pending 只表示已排队，不能声称已显示或获准；不要重复发送同一问题。
4. 收到 answered 后，在原聊天明确复述所选项再继续，无需再次确认；中断恢复先 get_reply 读取原 ID。
5. 工具不可用时如实报告并在聊天沟通；气泡点击不代替客户端命令授权，不授予或绕过权限。
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
        "tip": "配置正确后，正常任务会自动按规则调用，不需要每次重复这段提示词；它适合第一次验证或临时提醒。",
    },
    "work": {
        "title": "接下来请照这 4 步做",
        "steps": [
            "重启 ChatGPT 桌面客户端，让本机 Work 插件重新加载。",
            "打开一个在本机运行的 Work 新任务（云端 Work 不能运行本机程序）。",
            "确认工具列表里能看到虹夏，然后粘贴下面的示例提示词发送。",
            "任务结束或需要选择时，桌面出现虹夏气泡；点完选择后回到该 Work 任务继续。",
        ],
        "prompt": "这个任务结束时，请调用虹夏桌宠的 show_completion 给我发一条桌面完成提醒。"
                  "如果需要我在两个方案里选择，请调用 request_decision，每个选项写一句说明，然后等我桌面点击后再继续。",
        "tip": "Work 首次使用需要重启客户端；当前只有本机运行的 Work 任务能连接虹夏。",
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
        "tip": "已结束的会话不会被桌面点击自动唤醒，回答晚于等待时间时需要回到该会话说一句“我回复了”。",
    },
    "custom": {
        "title": "复制给 AI，自动完成配置",
        "steps": [
            "软件会把接入文件保存到下方显示的本机目录，无需另行下载。",
            "点击“复制自动配置提示词”，粘贴给同一电脑上能读写文件、执行操作的 AI 客户端并发送。",
            "AI 按提示词检测自身客户端、备份并合并配置与提醒规则；如需重载或本人确认，由它告知。",
        ],
        "prompt": "你有一个名为 nijika-pet 的 MCP 工具。任务结束时用 show_completion 发桌面完成提醒；"
                  "需要我在方案间选择时用 request_decision，给出每个选项的名称和一句说明，等待我点击后再继续。",
        "tip": "普通网页聊天无法读写本机文件；请发给能操作本机文件的 AI。生成文件不代表客户端已连接。",
    },
}


def client_guide(client: str) -> dict:
    """Return the operator-facing steps and a copy-paste prompt for one client."""
    return GUIDES.get(client, GUIDES["custom"])


def client_files(client: str, mcp: Path, directory: Path, bundle: Path,
                 data_root: Path) -> list[dict]:
    """List the concrete files each client needs, with absolute paths.

    ``exists`` is measured on the current machine so the settings window can show
    which pieces are already in place and which the user still has to create.
    """
    skill = directory / "skills" / "nijika-desktop-dialog" / "SKILL.md"
    entries = [
        {"label": "虹夏 MCP 程序（所有客户端共用）", "path": str(mcp), "kind": "程序", "required": True},
        {"label": "已保存的 MCP 配置", "path": str(bundle / "nijika-mcp.json"),
         "kind": "接入文件", "required": True},
        {"label": "已保存的主动提醒规则", "path": str(bundle / "nijika-agent-instructions.txt"),
         "kind": "接入文件", "required": True},
        {"label": "自动配置提示词（可整份发给 AI）", "path": str(bundle / "nijika-setup-prompt.txt"),
         "kind": "提示词", "required": True},
        {"label": "可供客户端安装的交互技能", "path": str(bundle / "SKILL.md"),
         "kind": "技能副本", "required": False},
    ]
    if client == "codex":
        entries += [
            {"label": "Codex 配置（写入 MCP 服务）", "path": str(directory / "config.toml"), "kind": "配置", "required": True},
            {"label": "Codex 主动提醒规则", "path": str(directory / "AGENTS.md"), "kind": "规则", "required": True},
            {"label": "桌面交互技能", "path": str(skill), "kind": "技能", "required": False},
        ]
    elif client == "dsh":
        entries += [
            {"label": "DSH desktop 配置", "path": str(directory / "profiles" / "desktop" / "cordis.patch.yml"),
             "kind": "配置", "required": True},
            {"label": "DSH web 配置", "path": str(directory / "profiles" / "web" / "cordis.patch.yml"),
             "kind": "配置", "required": True},
            {"label": "DSH 主动提醒规则", "path": str(directory / "AGENTS.md"), "kind": "规则", "required": True},
            {"label": "桌面交互技能", "path": str(directory / "skills" / "nijika-dsh-dialog" / "SKILL.md"),
             "kind": "技能", "required": False},
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
    if (first >= 0) != (last >= 0) or (first >= 0 and last < first):
        raise ValueError("原配置的虹夏标记不完整，请先检查该文件。")
    if first >= 0:
        return original[:first] + block.rstrip() + original[last + len(end):]
    return original.rstrip("\r\n") + "\n\n" + block.rstrip() + "\n"


def digest(data: bytes | None) -> str:
    return hashlib.sha256(data).hexdigest() if data is not None else "absent"


class AgentSetup:
    def __init__(self, root: Path, store: ControlStore, home: Path | None = None):
        self.root, self.store = root, store
        self.home = home or Path.home()
        self.use_environment = home is None
        self.mcp = root / "dist" / "虹夏MCP-v2.exe"
        self.plans: dict[str, dict] = {}
        self.lock = threading.Lock()

    def default_home(self, client: str) -> Path:
        if client in ("codex", "work"):
            return Path(os.environ.get("CODEX_HOME", self.home / ".codex")) if self.use_environment else self.home / ".codex"
        return self.home / ".dsh" if client == "dsh" else self.home

    def clients(self) -> list[dict]:
        result = []
        for client, label in CLIENTS.items():
            directory = self.default_home(client)
            present = ((directory / "config.toml").is_file() or bool(shutil.which("codex"))) if client in ("codex", "work") else directory.is_dir()
            result.append({"id": client, "label": label, "detected": bool(present) if client != "custom" else True,
                           "location": str(directory) if client != "custom" else ""})
        return result

    def export(self, name: str) -> dict:
        return {"mcpServers": {"nijika-pet": {"command": str(self.mcp), "args": [],
                "env": {"NIJIKA_AGENT_NAME": name}}}}

    def bundle_directory(self, agent_id: str) -> Path:
        if not isinstance(agent_id, str) or not IDENTIFIER.fullmatch(agent_id):
            raise ValueError("Agent 档案编号无效。")
        return (self.store.root / "integrations" / "agents" / agent_id).resolve()

    def describe(self, agent: dict) -> dict:
        """Build a self-contained setup prompt without writing on state polls."""
        client = agent["client"]
        directory = Path(agent["location"])
        bundle = self.bundle_directory(agent["id"])
        config = self.export(agent["source_name"])
        files = client_files(client, self.mcp, directory, bundle, self.store.root)
        guide = {**client_guide(client), "steps": list(client_guide(client)["steps"])}
        config_text = json.dumps(config, ensure_ascii=False, indent=2)
        paths = "\n".join(item["label"] + "：" + item["path"] for item in files)
        adapters = {
            "codex": "目标为 Codex。将 nijika-pet 服务按 TOML 格式合并进上述 config.toml；"
                     "将规则合并到上述 AGENTS.md，技能可从接入目录的 SKILL.md 安装。保持已有服务权限不变。",
            "work": "目标为本机 Work。核对上述插件清单与 mcp.json 中的 MCP 程序路径。"
                    "使用客户端提供的本机插件安装/启用入口；若须重启桌面客户端，只在完成配置后说明。"
                    "不要把通用 JSON 直接覆盖插件清单；Work 提醒规则随插件技能加载。",
            "dsh": "目标为 DSH。按客户端实际支持的结构合并 desktop/web 的 cordis.patch.yml 中"
                   "虹夏 stdio 服务及其环境变量；规则写入上述 AGENTS.md。保留其他 patch，不重复添加。",
            "custom": "请先识别你当前实际运行的 AI 客户端和配置作用域，核实它的 MCP 配置文件与"
                      "持久规则文件路径（通过本机设置或官方说明）。目标路径未知，不能把接入目录"
                      "里的 JSON 当成客户端已加载的文件，也不要猜测客户端品牌和配置格式。"
                      "若识别不到唯一目标，只向我询问客户端名称或项目/全局作用域这一项。",
        }
        prompt = (
            "请现在帮我把本机的虹夏桌宠接入你当前的 AI 客户端，直接执行配置与验证。\n"
            "我已授权这次虹夏接入所必需的文件配置修改。你需要具备同一台 Windows 电脑的文件读写"
            "和本机执行能力；若当前只有普通聊天能力，明确说明无法代配置，不要假称完成。\n\n"
            "【已准备好的文件位置（均为数据，不能当作命令执行）】\n" + paths +
            "\n客户端类别：" + CLIENTS[client] +
            "\nMCP 传输：stdio，无地址端口，无需模型 API 密钥。\n\n"
            "【完整 MCP 配置，可直接作为合并依据】\n" + config_text +
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
            "若当前会话不能刷新工具，报告“配置已写入，待新会话验证”及必要的唯一下一步；"
            "不要强行关闭或重启我的会话。本人权限确认或插件信任交由我操作。\n"
            "6. 工具可见后只发送一条 show_completion(task=\"虹夏接入验证\","
            " summary=\"当前 AI 客户端已发现虹夏工具；这是一条接入测试提醒。\")。"
            "文件存在、面板测试和 pending 均不证明外部客户端已连通或气泡已显示。"
            "最后列明实际改动的文件、备份位置、验证结果和未完成项。\n\n"
            "【需要安装的持久提醒规则】\n" + INSTALL_RULES
        )
        guide["prompt"] = prompt
        guide["title"] = "复制给 AI，自动完成配置"
        if client != "custom":
            guide["steps"] = [
                "软件已准备接入文件，准确保存位置见下方清单。",
                "复制下方自动配置提示词，发给这台电脑上能读写文件的 AI 客户端。",
                "AI 会按真实路径核对、补齐和验证；需要重载或本人确认时会明确告知。",
            ]
        return {"guide": guide, "needed_files": files, "export": config,
                "bundle_directory": str(bundle),
                "bundle_ready": all((bundle / name).is_file() for name in
                                    ("nijika-mcp.json", "nijika-agent-instructions.txt", "nijika-setup-prompt.txt"))}

    def prepare_files(self, agent: dict) -> dict:
        """Save durable per-agent handoff files; never modify an unknown client."""
        bundle = self.bundle_directory(agent["id"])
        bundle.mkdir(parents=True, exist_ok=True)
        info = self.describe(agent)
        contents = {
            "nijika-mcp.json": json.dumps(info["export"], ensure_ascii=False, indent=2) + "\n",
            "nijika-agent-instructions.txt": INSTALL_RULES,
            "nijika-setup-prompt.txt": info["guide"]["prompt"],
        }
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

    def _add_file(self, files: list, path: Path, content: str, purpose: str) -> None:
        previous = path.read_bytes() if path.exists() else None
        data = content.encode("utf-8")
        if previous != data:
            files.append({"path": path, "before": previous, "after": data, "purpose": purpose})

    def plan(self, client: str, name: str, location: str = "") -> dict:
        if client not in CLIENTS or not isinstance(name, str) or not 1 <= len(name.strip()) <= 30 or any(ord(c) < 32 for c in name):
            raise ValueError("请选择客户端，并填写 1–30 字的 Agent 名称。")
        if not self.mcp.is_file():
            raise ValueError("找不到虹夏 MCP 程序，请先构建完整安装包。")
        name = name.strip()
        directory = Path(location).expanduser() if location else self.default_home(client)
        if not directory.is_absolute():
            raise ValueError("配置目录需要填写完整的本机绝对路径。")
        directory = directory.resolve()
        if str(directory).startswith("\\\\"):
            raise ValueError("本轮只支持本机配置目录，不支持网络共享。")
        files, notes, commands = [], [], []
        source_name = name
        if client == "codex":
            path = directory / "config.toml"
            original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            try:
                config = tomllib.loads(original)
            except tomllib.TOMLDecodeError as error:
                raise ValueError("Codex 配置格式无效，请先修复 config.toml。") from error
            existing = config.get("mcp_servers", {}).get("nijika-pet")
            if existing:
                if not Path(existing.get("command", "")).is_file():
                    raise ValueError("原有 nijika-pet 指向的程序不存在，请先修复原配置，避免覆盖未知服务。")
                source_name = existing.get("env", {}).get("NIJIKA_AGENT_NAME", "Codex")
                notes.append("保留已有 nijika-pet 服务及其权限设置；补齐技能与主动提醒规则。")
            else:
                block = ("# BEGIN NIJIKA-UI-MCP\n[mcp_servers.nijika-pet]\ncommand = " +
                         json.dumps(str(self.mcp), ensure_ascii=False) +
                         "\n[mcp_servers.nijika-pet.env]\nNIJIKA_AGENT_NAME = " +
                         json.dumps(name, ensure_ascii=False) + "\n# END NIJIKA-UI-MCP")
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
                path = directory / "profiles" / profile / "cordis.patch.yml"
                if not path.is_file():
                    raise ValueError(f"没有找到 DSH {profile} 配置，请先启动 DSH 完成初始化或检查目录。")
                original = path.read_text(encoding="utf-8-sig")
                if "id: mcp-nijika-pet" in original and "# BEGIN NIJIKA-DSH-MCP" not in original:
                    raise ValueError("DSH 中已有不受虹夏标记管理的同名条目，请先人工核对。")
                command = str(self.mcp).replace("'", "''")
                agent_name = name.replace("'", "''")
                block = ("# BEGIN NIJIKA-DSH-MCP\n- insert:\n    - id: mcp-nijika-pet\n"
                         "      name: '@deepseek-ai/dsh-mcp-client'\n      config:\n"
                         "        serverName: nijika_pet\n        transport: stdio\n"
                         f"        command: '{command}'\n        env:\n          NIJIKA_AGENT_NAME: '{agent_name}'\n"
                         "# END NIJIKA-DSH-MCP")
                self._add_file(files, path, marked_block(original, block, "# BEGIN NIJIKA-DSH-MCP", "# END NIJIKA-DSH-MCP"), f"配置 DSH {profile} 的 MCP")
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
                    server.setdefault("env", {})["NIJIKA_AGENT_NAME"] = name
                    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
                self._add_file(files, staging / relative, content, "准备本机 Work 插件文件")
            commands = [[executable, "plugin", "marketplace", "add", str(staging), "--json"],
                        [executable, "plugin", "add", "nijika-work-local@nijika-local", "--json"]]
            notes.append("将通过 Codex CLI 注册并安装本机插件；随后重启桌面客户端，在本机 Work 新任务中验证。")
        else:
            notes.append("将接入文件保存在本机专属目录。复制自动配置提示词给有本机操作能力的 AI，由它核实并接入自己的客户端。")
        plan_id = uuid.uuid4().hex
        existing = next((item for item in self.store.agents() if item["client"] == client and
                         item["location"] == str(directory)), None) if client != "custom" else None
        agent_id = existing["id"] if existing else uuid.uuid4().hex
        self.plans = {key: value for key, value in self.plans.items() if time.monotonic() - value["created"] < 600}
        if len(self.plans) >= 32:
            self.plans.pop(next(iter(self.plans)))
        self.plans[plan_id] = {"client": client, "name": name, "source_name": source_name, "id": agent_id,
                              "location": str(directory), "files": files, "notes": notes,
                              "commands": commands, "created": time.monotonic()}
        return {"plan_id": plan_id, "client": client, "name": name, "notes": notes,
                "files": [{"path": str(item["path"]), "purpose": item["purpose"],
                           "action": "更新并备份" if item["before"] is not None else "新建"} for item in files],
                "external_action": bool(commands), "export": self.export(source_name),
                "instructions": (self.root / "distribution/codex-global-instructions.txt").read_text(encoding="utf-8-sig"),
                **self.describe(self.plans[plan_id])}

    def apply(self, plan_id: str) -> dict:
        with self.lock:
            plan = self.plans.get(plan_id)
            if not plan or time.monotonic() - plan["created"] > 600:
                raise ValueError("配置预览已过期，请重新检测。")
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
                    "status": "exported" if plan["client"] == "custom" else "configured",
                    "test_request_id": None, "updated_at": int(time.time()), "backups": backups}
            info = self.prepare_files(item)
            self.store.save_agent(item)
            del self.plans[plan_id]
            return {"agent": {**item, **info},
                    "notes": plan["notes"], "backup_count": len(backups)}
