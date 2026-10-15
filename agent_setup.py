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

from control_store import ControlStore

CLIENTS = {"codex": "Codex", "work": "ChatGPT Work", "dsh": "DeepSeek Harness", "custom": "其他 MCP 客户端"}


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
        return self.home / ".dsh"

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
            notes.append("生成标准 stdio MCP 配置与触发说明；需在所选客户端导入，不会自动修改未知客户端。")
        plan_id = uuid.uuid4().hex
        self.plans = {key: value for key, value in self.plans.items() if time.monotonic() - value["created"] < 600}
        if len(self.plans) >= 32:
            self.plans.pop(next(iter(self.plans)))
        self.plans[plan_id] = {"client": client, "name": name, "source_name": source_name,
                              "location": str(directory), "files": files, "notes": notes,
                              "commands": commands, "created": time.monotonic()}
        return {"plan_id": plan_id, "client": client, "name": name, "notes": notes,
                "files": [{"path": str(item["path"]), "purpose": item["purpose"],
                           "action": "更新并备份" if item["before"] is not None else "新建"} for item in files],
                "external_action": bool(commands), "export": self.export(source_name),
                "instructions": (self.root / "distribution/codex-global-instructions.txt").read_text(encoding="utf-8-sig")}

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
            existing = next((item for item in self.store.agents() if item["client"] == plan["client"] and
                             item["location"] == plan["location"]), None) if plan["client"] != "custom" else None
            item = {"id": existing["id"] if existing else uuid.uuid4().hex, "name": plan["name"],
                    "source_name": plan["source_name"], "client": plan["client"], "location": plan["location"],
                    "status": "exported" if plan["client"] == "custom" else "configured",
                    "test_request_id": None, "updated_at": int(time.time()), "backups": backups}
            self.store.save_agent(item)
            del self.plans[plan_id]
            return {"agent": item, "notes": plan["notes"], "backup_count": len(backups)}
