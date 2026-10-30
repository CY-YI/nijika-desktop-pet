"""Conservative, data-checked edits for the reviewed local setup adapters."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tomllib
from pathlib import Path


def repair_orphan_dsh_marker(original: str) -> str:
    """Remove a lone Nijika start marker when no managed service follows.

    Older auto-setup paths could leave this comment before MAGPIE-owned entries.
    Treating it as a valid block would make the next managed write unsafe. A
    marker paired with an actual managed ``mcp-nijika-pet`` entry is left alone
    for the regular strict parser to handle.
    """
    begin = list(re.finditer(r"(?m)^[ \t]*# BEGIN NIJIKA-DSH-MCP[ \t]*\r?$", original))
    end = list(re.finditer(r"(?m)^[ \t]*# END NIJIKA-DSH-MCP[ \t]*\r?$", original))
    if len(begin) != 1 or end or re.search(r"(?m)^\s*-?\s*id:\s*mcp-nijika-pet\s*(?:#.*)?$", original):
        return original
    start = begin[0].start()
    finish = begin[0].end()
    if original[finish:finish + 2] == "\r\n":
        finish += 2
    elif original[finish:finish + 1] in ("\n", "\r"):
        finish += 1
    return original[:start] + original[finish:]


def json_service_update(document: dict, mcp: Path, environment: dict[str, str],
                        client: str) -> dict:
    """Merge owned stdio services only; preserve unrelated fields and options."""
    result = copy.deepcopy(document)
    servers = result.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("MCP 服务列表格式无效；没有写入。")
    selected = {}
    for key, entry in servers.items():
        command = entry.get("command") if isinstance(entry, dict) else None
        path = Path(command) if isinstance(command, str) and command else None
        current = path is not None and path.is_absolute() and path.resolve() == mcp.resolve()
        candidate = path is not None and path.name.casefold() in ("虹夏mcp-v2.exe", "虹夏mcp.exe")
        if key not in ("nijika-pet", "nijika_pet") and not current and not candidate:
            continue
        same = (candidate and path.is_file() and mcp.is_file() and
                hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(mcp.read_bytes()).digest())
        if not (current or same) or not path.is_file():
            raise ValueError("同名服务或旧虹夏程序无法核实；没有写入或新增重复服务。")
        if entry.get("args", []) != [] or entry.get("type", "stdio") not in ("stdio", "local"):
            raise ValueError("已有虹夏服务参数或传输方式需人工核对；没有写入。")
        if not isinstance(entry.get("env", {}), dict):
            raise ValueError("虹夏环境变量格式无效。")
        selected[key] = entry
    def options(entry):
        value = copy.deepcopy(entry)
        for key in ("command", "args"):
            value.pop(key, None)
        value.setdefault("env", {})
        for key in ("NIJIKA_AGENT_NAME", "NIJIKA_HOST_NAME", "NIJIKA_PROFILE_ID"):
            value["env"].pop(key, None)
        return value
    chosen = copy.deepcopy(selected.get("nijika-pet", next(iter(selected.values()), {})))
    if any(options(entry) != options(chosen) for entry in selected.values()):
        raise ValueError("虹夏别名的权限或设置存在冲突；没有写入。")
    for key in selected:
        del servers[key]
    chosen.update(command=str(mcp), args=[])
    chosen.setdefault("env", {}).update(environment)
    if not selected and client == "copilot":
        chosen.update(type="local", tools=["*"])
    servers["nijika-pet"] = chosen
    return result


def remove_legacy_dsh_nijika_entry(original: str) -> str:
    """Edit only a legacy list item; unsupported YAML is left for manual review.

    No YAML dependency is needed at runtime. This deliberately accepts only the
    single-line scalar/block-list layout produced by the old manager.
    """
    if "magpie-mcp-nijika-pet" not in original:
        return original
    lines = original.splitlines(keepends=True)
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if re.search(r":\s*[|>]", text):
            raise ValueError("DSH 旧配置含跨行块，请人工核对；没有写入。")
        scalar = re.search(r":\s*(['\"])(.*)$", text)
        if scalar and not re.fullmatch(r".*" + scalar[1] + r"\s*(?:#.*)?", scalar[2]):
            raise ValueError("DSH 旧配置含跨行字符串，请人工核对；没有写入。")
    removed = set()
    found = 0
    for start, line in enumerate(lines):
        if not re.fullmatch(r"- insert:\s*(?:#.*)?", line.rstrip("\r\n")):
            continue
        end = start + 1
        while end < len(lines):
            text = lines[end].rstrip("\r\n")
            if text and not text[0].isspace() and not text.startswith("#"):
                break
            end += 1
        block = lines[start + 1:end]
        if not any("magpie-mcp-nijika-pet" in value for value in block):
            continue
        for value in block:
            text = value.strip()
            if not text or text.startswith("#"):
                continue
            # Reject multiline strings, anchors/aliases, flow-style nodes and
            # nonstandard indentation instead of guessing their boundaries.
            if ("\t" in value or not value.startswith("    ") or
                    re.search(r":\s*(?:[|>&*!]|[{[](?![}\]]\s*(?:#.*)?$))", text)):
                raise ValueError("DSH 旧条目含不支持的 YAML 结构，请人工核对；没有写入。")
            scalar = re.search(r":\s*(['\"])(.*)$", text)
            if scalar and not re.fullmatch(r".*" + scalar[1] + r"\s*(?:#.*)?", scalar[2]):
                raise ValueError("DSH 旧条目含跨行字符串，请人工核对；没有写入。")
        starts = [i for i in range(start + 1, end) if lines[i].startswith("    - ")]
        if any(lines[i].strip() and not lines[i].lstrip().startswith("#")
               for i in range(start + 1, starts[0] if starts else end)):
            raise ValueError("DSH 旧列表格式不受支持；没有写入。")
        kept = 0
        for pos, first in enumerate(starts):
            last = starts[pos + 1] if pos + 1 < len(starts) else end
            if not re.fullmatch(r"    - id: ['\"]?magpie-mcp-nijika-pet['\"]?\s*(?:#.*)?",
                                lines[first].rstrip("\r\n")):
                kept += 1
                continue
            item = "".join(lines[first:last])
            if not re.search(r"(?m)^        serverName: ['\"]?nijika[-_]pet['\"]?\s*(?:#.*)?$", item):
                raise ValueError("DSH 旧同名条目不能确认为虹夏服务；没有写入。")
            found += 1
            removed.update(range(first, last))
        if not kept:
            removed.update(range(start, end))
    if not found:
        raise ValueError("DSH 旧条目布局不受支持，请人工核对；没有写入。")
    return "".join(line for i, line in enumerate(lines)
                   if i not in removed or line.lstrip().startswith("#"))


def codex_service_update(original: str, mcp: Path, root: Path,
                         environment: dict[str, str], normalize_env) -> tuple[str, list[str]]:
    """Consolidate verified aliases, refusing conflicting options and programs."""
    before = tomllib.loads(original)
    servers = before.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError("Codex MCP 配置结构无效；没有写入。")
    selected = {}
    notes = []
    for key, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        command = entry.get("command", "")
        path = Path(command) if isinstance(command, str) and command else None
        current = path is not None and path.resolve() == mcp.resolve()
        source = (path is not None and path.name.lower() in ("python", "python.exe", "python3", "python3.exe")
                  and any(Path(str(arg)).resolve() == (root / "mcp_server.py").resolve()
                          for arg in entry.get("args", [])))
        if key not in ("nijika-pet", "nijika_pet") and not current and not source:
            continue
        same_binary = (path is not None and path.name in ("虹夏MCP.exe", "虹夏MCP-v2.exe")
                       and path.is_file() and hashlib.sha256(path.read_bytes()).digest()
                       == hashlib.sha256(mcp.read_bytes()).digest())
        if not (current or source or same_binary):
            raise ValueError(f"服务 {key} 指向未知服务或无法核实的旧虹夏程序，请先人工核对旧路径；没有写入，也未新增重复服务。")
        if not path.is_file():
            raise ValueError(f"服务 {key} 的原程序不存在，请先核对；没有写入。")
        if same_binary and not current and entry.get("args"):
            raise ValueError("旧虹夏程序带有额外参数，不能自动迁移；没有写入。")
        selected[key] = entry
    if not selected:
        return original, notes
    canonical = "nijika-pet" if "nijika-pet" in selected else next(iter(selected))
    chosen = copy.deepcopy(selected[canonical])
    def options(entry):
        value = copy.deepcopy(entry)
        value.pop("command", None)
        value.pop("args", None)
        value.setdefault("env", {})
        for field in ("NIJIKA_AGENT_NAME", "NIJIKA_HOST_NAME", "NIJIKA_PROFILE_ID"):
            value["env"].pop(field, None)
        return value
    if any(options(entry) != options(chosen) or entry.get("args", []) != chosen.get("args", [])
           for entry in selected.values()):
        raise ValueError("多个虹夏别名的权限、参数或其他配置冲突，请先人工核对；没有写入。")
    expected = copy.deepcopy(before)
    for key in selected:
        del expected["mcp_servers"][key]
    if Path(chosen["command"]).resolve() != mcp.resolve() and Path(chosen["command"]).name in ("虹夏MCP.exe", "虹夏MCP-v2.exe"):
        notes.append("已核对旧程序与当前程序摘要相同；将启动路径从 " + chosen["command"] + " 更新为 " + str(mcp))
        chosen["command"] = str(mcp)
    chosen.setdefault("env", {}).update(environment)
    expected["mcp_servers"]["nijika-pet"] = chosen
    # Parse individual header paths, including quoted table names/comments.
    # Final semantic equality guards against header-like lines inside strings.
    lines = original.splitlines(keepends=True)
    active = None
    result = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            try:
                table = tomllib.loads(stripped + "\n")
                path = []
                while isinstance(table, dict) and len(table) == 1:
                    name, table = next(iter(table.items()))
                    path.append(name)
                active = path if len(path) >= 2 and path[0] == "mcp_servers" and path[1] in selected else None
            except tomllib.TOMLDecodeError:
                active = None
            if active and active[1] == canonical:
                seen.add(canonical)
                header = "[mcp_servers.nijika-pet" + "".join(
                    "." + (p if re.fullmatch(r"[A-Za-z0-9_-]+", p) else json.dumps(p))
                    for p in active[2:]) + "]"
                comment = re.search(r"\]\s*(#.*)$", line.rstrip("\r\n"))
                line = header + (" " + comment[1] if comment else "") + "\n"
        if active and active[1] != canonical:
            continue
        if active and len(active) == 2 and re.match(r"^\s*command\s*=", line):
            line = "command = " + json.dumps(chosen["command"], ensure_ascii=False) + "\n"
        result.append(line)
    if canonical not in seen:
        raise ValueError("Codex 使用了不支持的内联服务格式，请人工核对；没有写入。")
    updated = normalize_env("".join(result), environment)
    if tomllib.loads(updated) != expected:
        raise ValueError("Codex 配置布局不支持安全迁移，请人工核对；没有写入。")
    if set(selected) != {"nijika-pet"}:
        notes.append("将已核实的虹夏别名合并为 nijika-pet，保留原服务选项；其他 MCP 不变。")
    return updated, notes
