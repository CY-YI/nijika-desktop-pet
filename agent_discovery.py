"""Bounded, read-only discovery. Evidence is not login or connection status."""
from __future__ import annotations

import hashlib
import json
import os
import re
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


def service_entries(path: Path) -> list[dict]:
    """Read only a conventional top-level MCP service table from one config."""
    raw = bounded_bytes(path)
    if path.suffix.casefold() == ".toml":
        data = tomllib.loads(raw.decode("utf-8-sig"))
        services = data.get("mcp_servers", data.get("mcpServers", {}))
    else:
        data = parse_json(raw)
        services = data.get("mcpServers", data.get("mcp_servers", data.get("mcp", {})))
    if not isinstance(services, dict):
        raise ValueError("Invalid servers")
    return [entry for key, entry in services.items()
            if key in ("nijika-pet", "nijika_pet") or nijika_candidate(entry)]


def preferred_config(paths: list[Path]) -> Path:
    """Use an existing config that actually contains an MCP table when possible."""
    existing = [path for path in paths if path.is_file()]
    for path in existing:
        try:
            service_entries(path)
            return path
        except (OSError, ValueError, TypeError):
            continue
    return existing[0] if existing else paths[0]


def magpie_states(home: Path, clients: set[str]) -> dict[str, dict]:
    """Inspect only Nijika routing; never return configuration or credential values."""
    path = home / ".config/magpie/library.json"
    states = {client: {"managed": False, "path": str(path), "digest": "absent", "error": False}
              for client in clients}
    if not states or not path.is_file():
        return states
    try:
        raw = bounded_bytes(path)
        data = parse_json(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        for state in states.values():
            state["digest"] = checksum
        entries = data.get("mcp", [])
        if not isinstance(entries, list):
            raise ValueError("Invalid library")
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("Invalid service")
            targets = item.get("agents", [])
            if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets):
                raise ValueError("Invalid targets")
            selected = clients.intersection("dsbot" if target == "ds-bot" else target for target in targets)
            if not selected:
                continue
            known = nijika_candidate(item)
            if known or item.get("name") in ("nijika-pet", "nijika_pet"):
                for client in selected:
                    state = states[client]
                    if not known or state["managed"]:
                        state["error"] = True
                    state["managed"] = state["managed"] or known
    except (OSError, ValueError, TypeError):
        for state in states.values():
            state["error"] = True
    return states


def magpie_state(home: Path, client: str) -> dict:
    return magpie_states(home, {client})[client]


def _yaml_scalar_values(text: str, key: str) -> list[str]:
    """Read only simple YAML scalar keys used by the generated DS Bot bundle."""
    values = []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*?)\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        raw = match.group(1)
        if raw.startswith("'") and raw.endswith("'"):
            values.append(raw[1:-1].replace("''", "'"))
        elif raw.startswith('"') and raw.endswith('"'):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw[1:-1]
            values.append(value)
        else:
            values.append(raw.split(" #", 1)[0].strip())
    return values


def dsbot_state(home: Path, executable: Path) -> dict:
    """Inspect the dedicated DS Bot stable bundle without reading credentials."""
    root = home / ".ds-bot"
    profile = root / "profiles/ds-bot/package.json"
    bundle_root = root / "integrations/nijika-dsbot-mcp"
    config = bundle_root / "cordis.patch.yml"
    skill = root / "skills/nijika-dsbot-dialog/SKILL.md"
    rules = root / "AGENTS.md"
    evidence, issues = [], []

    if root.is_dir():
        evidence.append("找到 DS Bot 用户目录")
    if profile.is_file():
        evidence.append("找到 DS Bot profile")
    if bundle_root.is_dir():
        evidence.append("找到虹夏稳定 bundle")
    if skill.is_file():
        evidence.append("找到主动提醒技能")

    profile_ok = False
    if profile.is_file():
        try:
            package = parse_json(bounded_bytes(profile))
            dependencies = package.get("dependencies", {})
            dsh = package.get("dsh", {})
            profile_data = dsh.get("profile", {}) if isinstance(dsh, dict) else {}
            if not isinstance(dependencies, dict) or not isinstance(profile_data, dict):
                raise ValueError("Invalid DS Bot profile")
            dependency = dependencies.get("@cy/nijika-dsbot-mcp")
            bundles = profile_data.get("bundles", [])
            dependency_path = None
            if isinstance(dependency, str) and dependency.startswith("link:"):
                dependency_path = Path(dependency[5:].replace("/", os.sep))
            profile_ok = (dependency_path is not None and
                          dependency_path.resolve() == bundle_root.resolve() and
                          isinstance(bundles, list) and
                          "@cy/nijika-dsbot-mcp" in bundles)
            if not profile_ok:
                issues.append("profile 尚未加载虹夏稳定 bundle，需重新运行 DS Bot 安装器。")
        except (OSError, ValueError, TypeError):
            issues.append("DS Bot profile 无法安全核对，请检查 package.json。")

    config_ok = False
    if config.is_file():
        try:
            text = bounded_bytes(config).decode("utf-8-sig")
            ids = re.findall(r"(?m)^\s*-\s*id\s*:\s*['\"]?nijika-dsbot-mcp['\"]?\s*$", text)
            servers = _yaml_scalar_values(text, "serverName")
            commands = _yaml_scalar_values(text, "command")
            agents = _yaml_scalar_values(text, "NIJIKA_AGENT_NAME")
            hosts = _yaml_scalar_values(text, "NIJIKA_HOST_NAME")
            if len(ids) != 1 or servers.count("nijika-pet") != 1:
                issues.append("虹夏 DS Bot 服务数量不唯一，接入前需预览去重。")
            elif len(commands) != 1:
                issues.append("稳定 bundle 中未找到唯一虹夏程序路径，需重新运行 DS Bot 安装器。")
            else:
                try:
                    command_ok = (Path(commands[0]).is_absolute() and
                                  Path(commands[0]).resolve() == executable.resolve())
                except (OSError, ValueError):
                    command_ok = False
                source_ok = agents == ["Agent"] and hosts == ["DS Bot"]
                config_ok = command_ok and source_ok and len(ids) == 1
                if not command_ok:
                    issues.append("稳定 bundle 中的虹夏程序路径需核对。")
                if not source_ok:
                    issues.append("虹夏来源应为 Agent · DS Bot，需重新运行 DS Bot 安装器。")
        except (OSError, UnicodeError, ValueError, TypeError):
            issues.append("DS Bot 稳定 bundle 无法安全核对，请检查 cordis.patch.yml。")

    rules_ok = False
    if rules.is_file():
        try:
            text = bounded_bytes(rules).decode("utf-8-sig")
            start = "# BEGIN NIJIKA-DSBOT-DIALOG"
            end = "# END NIJIKA-DSBOT-DIALOG"
            rules_ok = text.count(start) == 1 and text.count(end) == 1
            if rules_ok:
                evidence.append("找到结束提醒规则")
        except (OSError, UnicodeError, ValueError):
            pass
    skill_ok = skill.is_file()
    if skill_ok and rules_ok and not config.is_file():
        issues.append("主动提醒技能已存在，但虹夏 MCP bundle 尚未安装。")
    elif not skill_ok or not rules_ok:
        issues.append("主动提醒技能或结束规则不完整，需重新运行 DS Bot 安装器。")

    found = bool(evidence)
    if not found:
        issues = []
    configured = profile_ok and config_ok and skill_ok and rules_ok and not issues
    return {
        "root": root, "profile": profile, "bundle_root": bundle_root,
        "config": config, "skill": skill, "rules": rules,
        "bundle_registered": profile_ok,
        "evidence": evidence, "issue": "；".join(dict.fromkeys(issues)),
        "found": found, "configured": configured,
    }


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
        manager = magpie_state(home, client)
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
                       "issue": issue, "status": "需核对" if issue else
                       "MAGPIE 管理" if manager["managed"] else "发现虹夏配置" if exact else
                       "发现 Work 启动依赖" if evidence and client == "work" else
                       "已发现入口" if evidence else "未发现入口",
                       "verification": "尚未验证宿主调用"})
    extra_specs = (
        ("workbuddy", "WorkBuddy", [".workbuddy/mcp.json"], "WorkBuddy", None),
        ("workbuddy-ai", "WorkBuddy AI", [".workbuddy-ai/mcp.json"], "WorkBuddy AI", None),
        ("grok", "Grok Build", [".grok/config.toml"], "Grok Build", "grok"),
        ("cursor", "Cursor", [".cursor/mcp.json"], "Cursor", "cursor-agent"),
        ("antigravity", "Antigravity",
         [".antigravity/mcp.json", ".antigravity/settings.json"], "Antigravity", "antigravity"),
        ("codebuddy", "CodeBuddy", [".codebuddy/mcp.json"], "CodeBuddy", "codebuddy"),
        ("openmausbot", "OpenMausBot", [".openmausbot/config.json"], "OpenMausBot", None),
        ("openclaw", "OpenClaw", [".openclaw/openclaw.json"], "OpenClaw", "openclaw"),
        ("vscode", "VS Code", ["AppData/Roaming/Code/User/mcp.json",
                               "AppData/Roaming/Code/User/settings.json"], "VS Code", "code"),
        ("obsidian", "Obsidian", ["AppData/Roaming/obsidian/obsidian.json"], "Obsidian", None),
        ("claude-desktop", "Claude Desktop",
         ["AppData/Local/Claude/claude_desktop_config.json",
          "AppData/Roaming/Claude/claude_desktop_config.json",
          "AppData/Local/Claude-3p/claude_desktop_config.json",
          "AppData/Roaming/Claude-3p/claude_desktop_config.json",
          "AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/claude_desktop_config.json"],
         "Claude Desktop", None),
    )
    for client, label, relatives, software, command in extra_specs:
        paths = [home / relative for relative in relatives]
        path = preferred_config(paths)
        evidence, entries, issue = [], [], ""
        if path.is_file():
            evidence.append("找到已知配置")
            try:
                entries = service_entries(path)
            except (OSError, ValueError, TypeError):
                issue = "配置无法安全读取，请先核对格式或文件大小；未返回配置内容。"
        if command and which(command):
            evidence.append("找到命令入口")
        exact = len(entries) == 1 and known_service(entries[0], executable)
        if len(entries) > 1:
            issue = "发现多个虹夏服务，接入前需预览去重。"
        elif entries and not exact:
            issue = "虹夏服务路径需核对，预览时只接受可验证程序。"
        manager = magpie_state(home, client)
        if manager["error"]:
            issue = "MAGPIE 库无法安全读取，不能确定管理归属。"
        found = bool(evidence)
        result.append({
            "id": client, "label": label, "detected": found, "mode": "guided",
            "location": str(path.parent), "config_path": str(path),
            "evidence": evidence,
            "manager": "magpie" if manager["managed"] else "nijika",
            "configuration": "found" if exact else "not_verified",
            "software": software,
            "status": ("需核对" if issue else
                       "MAGPIE 管理" if manager["managed"] else
                       "发现虹夏配置" if exact else
                       "已发现入口" if found else "未发现入口"),
            "issue": issue,
            "verification": "尚未验证宿主调用" if exact else
                            "具体格式或作用域仍需在真实宿主核对",
        })
    dsbot = dsbot_state(home, executable)
    manager = magpie_state(home, "dsbot")
    issue = dsbot["issue"]
    if manager["error"]:
        issue = "MAGPIE 库无法安全读取，不能确定管理归属。"
    elif manager["managed"]:
        issue = ("已分发 MAGPIE MCP，但仍找到旧虹夏 bundle 入口；在 DS Bot 核对是否重复加载。"
                 if dsbot["bundle_registered"] else "")
    else:
        issue = issue.replace("重新运行 DS Bot 安装器", "在 MAGPIE 核对 MCP 和统一提醒规则")
    result.append({
        "id": "dsbot", "label": "DS Bot", "detected": dsbot["found"],
        "mode": "guided", "location": str(dsbot["root"]),
        "config_path": str(dsbot["config"]),
        "evidence": dsbot["evidence"],
        "manager": "magpie" if manager["managed"] else "nijika",
        "configuration": "found" if dsbot["configured"] else "not_verified",
        "software": "DS Bot",
        "status": ("需核对" if issue else
                   "MAGPIE 管理" if manager["managed"] else
                   "发现虹夏配置" if dsbot["configured"] else
                   "已发现入口" if dsbot["found"] else "未发现入口"),
        "issue": issue,
        "verification": "尚未验证宿主调用" if dsbot["configured"] else
                        "需在 DS Bot 新任务中验证实际调用",
    })
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
