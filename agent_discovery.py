"""Bounded, read-only discovery. Evidence is not login or connection status."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tomllib
from pathlib import Path

CLIENTS = {"codex": "Codex", "work": "ChatGPT Work", "dsh": "DeepSeek Harness",
           "claude": "Claude Code", "gemini": "Gemini CLI", "copilot": "Copilot CLI",
           "custom": "其他 MCP 客户端"}
JSON_CLIENTS = {
    "claude": (".claude.json", ".claude/CLAUDE.md", "Claude", "Claude Code"),
    "gemini": ("settings.json", "GEMINI.md", "Gemini", "Gemini CLI"),
    "copilot": ("mcp-config.json", "copilot-instructions.md", "Copilot", "Copilot CLI"),
}
CANONICAL_NAMES = {"codex": "Codex", "work": "Work", "dsh": "DSH",
                   **{key: value[3] for key, value in JSON_CLIENTS.items()}}
MAX_CONFIG = 2 * 1024 * 1024


def parse_json(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("配置含重复字段，请先核对原文件。")
            result[key] = value
        return result
    if len(raw) > MAX_CONFIG:
        raise ValueError("配置超过 2 MB，请使用手动接入并核对目标作用域。")
    try:
        result = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    except UnicodeDecodeError as error:
        raise ValueError("配置不是有效 UTF-8 文本。") from error
    if not isinstance(result, dict):
        raise ValueError("客户端配置需要 JSON 对象。")
    return result


def bounded_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(MAX_CONFIG + 1)
    if len(raw) > MAX_CONFIG:
        raise ValueError("配置超过 2 MB，请使用手动接入并核对目标作用域。")
    return raw


def read_json(path: Path) -> dict:
    return parse_json(bounded_bytes(path))


def client_home(client: str, home: Path, use_environment: bool) -> Path:
    defaults = {"codex": home / ".codex", "work": home / ".codex",
                "dsh": home / ".dsh", "claude": home,
                "gemini": home / ".gemini", "copilot": home / ".copilot"}
    overrides = {"codex": "CODEX_HOME", "work": "CODEX_HOME", "copilot": "COPILOT_HOME"}
    value = os.environ.get(overrides.get(client, "")) if use_environment else None
    return Path(value) if value else defaults.get(client, home)


def json_paths(client: str, directory: Path) -> tuple[Path, Path]:
    config, rules, _, _ = JSON_CLIENTS[client]
    return directory / config, directory / rules


def known_service(entry: object, executable: Path) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("command"), str):
        return False
    path = Path(entry["command"])
    return path.is_absolute() and path.resolve() == executable.resolve()


def nijika_candidate(entry: object) -> bool:
    return (isinstance(entry, dict) and isinstance(entry.get("command"), str) and
            Path(entry["command"].replace("\\", "/")).name.casefold()
            in {"虹夏mcp-v2.exe", "虹夏mcp.exe"})


def magpie_state(home: Path, client: str, *, use_environment: bool = False) -> dict:
    """Inspect Nijika routing without exposing environment or credential values."""
    config_home = os.environ.get("XDG_CONFIG_HOME") if use_environment else None
    directory = Path(config_home).expanduser() if config_home else home / ".config"
    path = directory / "magpie/library.json"
    result = {"managed": False, "path": str(path), "digest": "absent", "error": False,
              "route": "unknown", "service_name": "", "command": "", "targets": [],
              "identity_compatible": False, "arguments_compatible": False,
              "hub_enabled": False, "policy": "unknown"}
    if not directory.is_absolute():
        result["error"] = True
        return result
    if not path.is_file():
        return result
    try:
        raw = bounded_bytes(path)
        data = parse_json(raw)
        result["digest"] = hashlib.sha256(raw).hexdigest()
        entries = data.get("mcp", [])
        if not isinstance(entries, list):
            raise ValueError("Invalid library")
        hub = data.get("mcpHub", False)
        if not isinstance(hub, bool):
            raise ValueError("Invalid MCP router setting")
        result["hub_enabled"] = hub
        # Magpie v0.1.4078 hubFor cannot give its HTTP hub to Claude Desktop,
        # or publish it under a name already used by a library service.
        hub_available = (hub and client != "claude-desktop" and
                         not any(isinstance(row, dict) and row.get("name") == "magpie" for row in entries))
        names = set()
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("Invalid service")
            # The Magpie CLI changes a service by name across its whole library.
            name = item.get("name")
            if name in ("nijika-pet", "nijika_pet"):
                if name in names:
                    raise ValueError("Ambiguous Magpie service name")
                names.add(name)
            targets = item.get("agents", [])
            if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets):
                raise ValueError("Invalid targets")
            if client in targets and (nijika_candidate(item) or item.get("name") in ("nijika-pet", "nijika_pet")):
                if not nijika_candidate(item) or result["managed"]:
                    raise ValueError("Unknown managed service")
                route = item.get("hub", "")
                if route not in ("", "shared", "direct"):
                    raise ValueError("Unknown MCP router policy")
                result["managed"] = True
                result["route"] = "shared" if hub_available and route != "direct" else "direct"
                result["policy"] = "direct" if route == "direct" else "shared"
                result["service_name"] = str(item.get("name", ""))
                result["command"] = item["command"]
                result["targets"] = list(targets)
                result["arguments_compatible"] = item.get("args", []) == []
                if item.get("transport", "stdio") != "stdio" or item.get("url"):
                    result["arguments_compatible"] = False
                environment = item.get("env", {})
                if isinstance(environment, dict):
                    # Windows environment variable names are case-insensitive.
                    normalized = {key.upper(): value for key, value in environment.items()}
                    agent = normalized.get("NIJIKA_AGENT_NAME", "auto")
                    host = normalized.get("NIJIKA_HOST_NAME", "")
                    result["identity_compatible"] = (len(normalized) == len(environment)
                                                     and isinstance(agent, str) and agent.strip().casefold() in {"", "auto", "agent"}
                                                     and isinstance(host, str) and not host.strip()
                                                     and not normalized.get("NIJIKA_PROFILE_ID"))
    except (OSError, ValueError, TypeError):
        result["error"] = True
    return result


def ds_bot_location(home: Path, *, use_environment: bool = False) -> dict:
    """Discover DS Bot's standalone data root without reading its Bot state."""
    override = os.environ.get("DS_BOT_HOME") if use_environment else None
    shell = os.environ.get("DS_BOT_SHELL_DATA") if use_environment else None
    shell_root = Path(shell).expanduser() if shell else home / "AppData/Roaming/DS Bot"
    locations = shell_root / "locations.json"
    if not shell and not locations.is_file():
        previous = home / "AppData/Roaming/DeepSeek Bot/locations.json"
        if previous.is_file():
            locations = previous
    try:
        if shell and (not shell_root.is_absolute() or str(shell_root).startswith("\\\\")):
            raise ValueError("Unsupported shell data directory")
        if override:
            directory = Path(override).expanduser()
        elif locations.is_file():
            value = read_json(locations).get("dataDir")
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Missing data directory")
            directory = Path(value).expanduser()
        else:
            directory = home / ".ds-bot"
        if not directory.is_absolute() or str(directory).startswith("\\\\"):
            raise ValueError("Unsupported data directory")
        directory = directory.resolve()
        profile = directory / "profiles/ds-bot/cordis.patch.yml"
        detected = profile.is_file() or (locations.is_file() and directory.is_dir())
        return {"detected": detected, "location": str(directory), "config_path": str(profile), "issue": ""}
    except (OSError, ValueError, TypeError):
        return {"detected": locations.is_file() or bool(override), "location": "",
                "config_path": str(locations),
                "issue": "DS Bot 的数据目录无法安全确认，请在 DS Bot 设置中核对；未读取 Bot 数据。"}


def scan(home: Path, executable: Path, *, use_environment: bool = False,
         which=None) -> list[dict]:
    which = which or shutil.which
    result = []
    for client, label in CLIENTS.items():
        if client == "custom":
            continue
        directory = client_home(client, home, use_environment)
        evidence, entries, issue = [], [], ""
        config = None
        if client in JSON_CLIENTS:
            config = json_paths(client, directory)[0]
        elif client == "codex":
            config = directory / "config.toml"
        elif client == "dsh":
            config = directory / "profiles/desktop/cordis.patch.yml"
        elif client == "work":
            config = directory / "plugins"
        command = "codex" if client == "work" else client
        if which(command):
            evidence.append("找到命令入口" if client != "work" else "找到 Codex CLI 启动依赖")
        if config and config.exists():
            evidence.append("找到客户端配置" if client != "work" else "找到本机插件目录")
        try:
            if config and config.is_file() and client in JSON_CLIENTS:
                data = read_json(config)
                services = data.get("mcpServers", {})
                if not isinstance(services, dict):
                    raise ValueError("Invalid servers")
                entries = [entry for key, entry in services.items()
                           if key in ("nijika-pet", "nijika_pet") or nijika_candidate(entry)]
                # Claude project scopes may shadow the global service.
                if client == "claude" and isinstance(data.get("projects"), dict):
                    if any(isinstance(project, dict) and isinstance(project.get("mcpServers"), dict) and
                           any(key in ("nijika-pet", "nijika_pet") or nijika_candidate(value)
                               for key, value in project["mcpServers"].items())
                           for project in data["projects"].values()):
                        issue = "发现项目作用域虹夏配置，需核对作用域优先级。"
            elif config and config.is_file() and client == "codex":
                services = tomllib.loads(bounded_bytes(config).decode("utf-8-sig")).get("mcp_servers", {})
                if not isinstance(services, dict):
                    raise ValueError("Invalid servers")
                entries = [entry for key, entry in services.items()
                           if key in ("nijika-pet", "nijika_pet") or nijika_candidate(entry)]
            elif config and config.is_file() and client == "dsh":
                # Parsing/writing YAML is the existing adapter's responsibility.
                text = bounded_bytes(config).decode("utf-8-sig")
                if "mcp-nijika-pet" in text:
                    evidence.append("发现虹夏配置标记（未验证加载）")
        except (OSError, ValueError, TypeError):
            issue = "配置无法安全读取，请先核对格式或文件大小；未返回配置内容。"
        manager = magpie_state(home, client, use_environment=use_environment)
        if manager["error"]:
            issue = "MAGPIE 库无法安全读取，不能确定管理归属。"
        exact = len(entries) == 1 and known_service(entries[0], executable)
        if len(entries) > 1:
            issue = "发现多个虹夏服务，接入前需预览去重。"
        elif entries and not exact:
            issue = "虹夏服务路径需核对，预览时只接受可验证程序。"
        result.append({"id": client, "label": label, "location": str(directory),
                       "detected": bool(evidence), "mode": "automatic",
                       "evidence": evidence, "configuration": "found" if exact else "not_verified",
                       "config_path": str(config), "manager": "magpie" if manager["managed"] else "nijika",
                       "issue": issue, "magpie_route": manager["route"], "status": "需核对" if issue else
                       "MAGPIE 管理" if manager["managed"] else "发现虹夏配置" if exact else
                       "发现 Work 启动依赖" if evidence and client == "work" else
                       "已发现入口" if evidence else "未发现入口",
                       "verification": "尚未验证宿主调用"})
    for client, label, relative, software in (
        ("workbuddy", "WorkBuddy", ".workbuddy/mcp.json", "WorkBuddy"),
        ("workbuddy-ai", "WorkBuddy AI", ".workbuddy-ai/mcp.json", "WorkBuddy AI"),
        ("vscode", "VS Code", "AppData/Roaming/Code/User/settings.json", "VS Code"),
        ("obsidian", "Obsidian", "AppData/Roaming/obsidian/obsidian.json", "Obsidian"),
        ("claude-desktop", "Claude Desktop", "AppData/Roaming/Claude/claude_desktop_config.json", "Claude Desktop"),
    ):
        path = home / relative
        # Also inspect the known Store distribution, without reading account data.
        if client == "claude-desktop" and not path.is_file():
            store = home / "AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/claude_desktop_config.json"
            if store.is_file():
                path = store
        found = path.is_file() or (client == "vscode" and bool(which("code")))
        manager = magpie_state(home, client, use_environment=use_environment)
        issue = "MAGPIE 库无法安全读取，不能确定管理归属。" if manager["error"] else ""
        result.append({"id": client, "label": label, "detected": found, "mode": "guided",
                       "location": str(path.parent), "config_path": str(path),
                       "evidence": ["找到已知入口/配置"] if found else [],
                       "manager": "magpie" if manager["managed"] else "nijika", "magpie_route": manager["route"],
                       "configuration": "not_verified", "software": software,
                       "status": "需核对" if issue else "可生成指引" if found else "未发现入口",
                       "issue": issue, "verification": "扩展/工作区格式需接收方 AI 核实"})
    bot = ds_bot_location(home, use_environment=use_environment)
    manager = magpie_state(home, "ds-bot", use_environment=use_environment)
    issue = bot["issue"] or ("MAGPIE 库无法安全读取，不能确定管理归属。" if manager["error"] else "")
    result.append({"id": "ds-bot", "label": "DS Bot 独立版", **bot, "mode": "guided",
                   "evidence": ["找到独立版数据目录"] if bot["detected"] else [],
                   "manager": "magpie" if manager["managed"] else "nijika",
                   "magpie_route": manager["route"], "configuration": "not_verified", "software": "DS Bot",
                   "status": "需核对" if issue else "可生成指引" if bot["detected"] else "未发现入口",
                   "issue": issue, "verification": "需在具体 Bot 中验证工具调用和来源"})
    # VS Code extensions are separate routes.  Keep the generic editor entry
    # for manual configuration, then add only manifests we can verify locally.
    try:
        from vscode_agents import discover as discover_vscode
        result.extend(discover_vscode(home))
    except (OSError, ValueError, TypeError):
        # Discovery is advisory; a malformed extension manifest must not block
        # the other client results.
        pass
    return result
