"""Audit/fix only known local Nijika stdio aliases; never export other settings.

Default is read-only. --apply requires --backup, saves only Nijika fragments,
checks unrelated parsed settings are unchanged, and refuses concurrent writes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_discovery import magpie_state
from notice_source import resolve_source


def is_nijika(entry):
    return (isinstance(entry, dict) and
            Path(str(entry.get("command", "")).replace("\\", "/")).name.casefold()
            in {"虹夏mcp-v2.exe", "虹夏mcp.exe"})


def env_for(host):
    if host == "auto":
        return {"NIJIKA_AGENT_NAME": "auto"}
    source = resolve_source(host)
    return {"NIJIKA_AGENT_NAME": source.agent, "NIJIKA_HOST_NAME": source.software}


def repair_servers(data, host, changes):
    """Recursively cover Claude project scopes as well as global mcpServers."""
    if not isinstance(data, dict):
        return
    for key, value in list(data.items()):
        if key == "mcpServers" and isinstance(value, dict):
            selected = {k: v for k, v in value.items() if is_nijika(v)}
            if not selected:
                continue
            canonical = "nijika-pet" if "nijika-pet" in selected else next(iter(selected))
            changes.append({"scope": "mcpServers", "before": copy.deepcopy(selected)})
            entry = copy.deepcopy(selected[canonical])
            entry.setdefault("env", {}).update(env_for(host))
            for alias in selected:
                del value[alias]
            value[canonical] = entry
        elif isinstance(value, dict):
            repair_servers(value, host, changes)


def without_servers(data):
    data = copy.deepcopy(data)
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if key == "mcpServers" and isinstance(value, dict):
                data[key] = {k: v for k, v in value.items() if not is_nijika(v)}
            elif isinstance(value, dict):
                data[key] = without_servers(value)
    return data


def patch_json(text, host):
    before = json.loads(text)
    after = copy.deepcopy(before)
    fragments = []
    repair_servers(after, host, fragments)
    assert without_servers(before) == without_servers(after), "unrelated JSON changed"
    return json.dumps(after, ensure_ascii=False, indent=2) + "\n", fragments


def patch_library(text):
    before = json.loads(text)
    after = copy.deepcopy(before)
    entries = [v for v in after.get("mcp", []) if is_nijika(v)]
    if not entries:
        return text, []
    first_index = next(i for i, value in enumerate(after.get("mcp", [])) if is_nijika(value))
    targets = sorted({c for entry in entries for c in entry.get("agents", [])})
    entry = copy.deepcopy(next((v for v in entries if v.get("name") == "nijika-pet"), entries[0]))
    entry["name"], entry["agents"] = "nijika-pet", targets
    entry["env"] = {**entry.get("env", {}), **env_for("auto")}
    entry["env"].pop("NIJIKA_HOST_NAME", None)
    remaining = [value for value in after["mcp"] if not is_nijika(value)]
    remaining.insert(min(first_index, len(remaining)), entry)
    after["mcp"] = remaining
    skills_before = [copy.deepcopy(v) for v in after.get("skills", [])
                     if v.get("name") in {"nijika-desktop-dialog", "nijika-dsh-dialog"}]
    # Keep original access scope; remove DSH-specific double instructions from
    # other products, and the Codex version from DSH.
    for skill in after.get("skills", []):
        if skill.get("name") == "nijika-dsh-dialog":
            skill["agents"] = [v for v in skill.get("agents", []) if v == "dsh"]
        if skill.get("name") == "nijika-desktop-dialog":
            skill["agents"] = [v for v in skill.get("agents", []) if v != "dsh"]
    filtered = lambda x: {**x, "mcp": [v for v in x.get("mcp", []) if not is_nijika(v)],
                         "skills": [v for v in x.get("skills", []) if v.get("name") not in
                                    {"nijika-desktop-dialog", "nijika-dsh-dialog"}]}
    assert filtered(before) == filtered(after), "unrelated library changed"
    return json.dumps(after, ensure_ascii=False, indent=2) + "\n", [
        {"scope": "library", "before": entries, "skills_before": skills_before}]


def patch_toml(text, host):
    before = tomllib.loads(text)
    entries = before.get("mcp_servers", {})
    selected = {k: v for k, v in entries.items() if is_nijika(v)}
    if not selected:
        return text, []
    canonical = "nijika-pet" if "nijika-pet" in selected else next(iter(selected))
    entry = copy.deepcopy(selected[canonical])
    # Keep all extra server options and environment fields, including trust,
    # but edit only the identity values. tomli_w is intentionally not required.
    from agent_setup import normalize_codex_agent_name
    # Canonicalize just known table names, never arbitrary TOML strings.
    result = text
    if canonical != "nijika-pet":
        result = re.sub(r'(?m)^(\[mcp_servers\.)' + re.escape(canonical) + r'(?=[.\]])',
                        r'\1nijika-pet', result)
    for alias in selected:
        if alias == canonical:
            continue
        result = re.sub(r'(?ms)^\[mcp_servers\.' + re.escape(alias) +
                        r'(?:\.[^\]]+)?\][^\n]*\n.*?(?=^\[|\Z)', '', result)
    # The known local file uses table-style env; handle inline env safely too.
    env = env_for(host)
    result = normalize_codex_agent_name(result, env["NIJIKA_AGENT_NAME"])
    parsed = tomllib.loads(result)
    current = parsed["mcp_servers"]["nijika-pet"].get("env", {})
    if "NIJIKA_HOST_NAME" in current:
        # Restrict substitutions to the selected env section.
        result = re.sub(r'(?ms)(^\[mcp_servers\.nijika-pet\.env\]\n)(.*?)(?=^\[|\Z)',
                        lambda m: m[1] + re.sub(r'(?m)^NIJIKA_HOST_NAME\s*=.*$',
                            "NIJIKA_HOST_NAME = " + json.dumps(env["NIJIKA_HOST_NAME"]), m[2]), result)
    elif re.search(r'(?m)^\[mcp_servers\.nijika-pet\.env\]\s*$', result):
        result = re.sub(r'(?m)^(\[mcp_servers\.nijika-pet\.env\]\s*)$',
                        lambda m: m[1] + "\nNIJIKA_HOST_NAME = " + json.dumps(env["NIJIKA_HOST_NAME"]), result)
    else:
        pattern = r'(?ms)(^\[mcp_servers\.nijika-pet\][^\n]*\n)(.*?)(?=^\[|\Z)'
        def add_host(match):
            body, count = re.subn(
                r'(?m)^(\s*env\s*=\s*\{)(.*)(\}\s*)$',
                lambda m: m[1] + m[2].rstrip().rstrip(",") +
                ", NIJIKA_HOST_NAME = " + json.dumps(env["NIJIKA_HOST_NAME"]) + m[3], match[2])
            if count != 1:
                raise ValueError("unsupported TOML env layout; no write")
            return match[1] + body
        result = re.sub(pattern, add_host, result)
    after = tomllib.loads(result)
    expected = copy.deepcopy(before)
    for key in selected:
        del expected["mcp_servers"][key]
    entry.setdefault("env", {}).update(env)
    expected["mcp_servers"]["nijika-pet"] = entry
    assert expected == after, "unexpected TOML change"
    return result, [{"scope": "mcp_servers", "before": selected}]


def patch_dsh(text, host):
    import yaml  # Optional audit-tool dependency; not a runtime dependency.
    before = yaml.safe_load(text)
    def is_entry(node):
        values = node.get("insert", []) if isinstance(node, dict) else []
        return isinstance(values, list) and len(values) == 1 and is_nijika(values[0].get("config"))
    selected = [v for v in before if is_entry(v)]
    if not selected:
        return text, []
    entry = copy.deepcopy(selected[0])
    entry["insert"][0]["id"] = "magpie-mcp-nijika-pet"
    config = entry["insert"][0]["config"]
    config["serverName"] = "nijika-pet"
    config.setdefault("env", {}).update(env_for(host))
    pattern = re.compile(r'(?ms)^- insert:[^\n]*\n.*?(?=^- |\Z)')
    result = pattern.sub(lambda m: "" if is_entry((yaml.safe_load(m[0]) or [{}])[0]) else m[0], text)
    result = result.rstrip() + "\n" + yaml.safe_dump([entry], allow_unicode=True, sort_keys=False)
    after = yaml.safe_load(result)
    assert [v for v in before if not is_entry(v)] == [v for v in after if not is_entry(v)], "unrelated YAML changed"
    return result, [{"scope": "dsh inserts", "before": selected}]


def targets(home):
    yield "Shared Magpie", home / ".config/magpie/library.json", "auto", None, patch_library
    for label, rel, host, manager_client in (
        ("Codex", ".codex/config.toml", "Codex", "codex"),
        ("Claude Code", ".claude.json", "Claude Code", "claude"),
        ("Gemini CLI", ".gemini/settings.json", "Gemini CLI", "gemini"),
        ("Copilot CLI", ".copilot/mcp-config.json", "Copilot CLI", "copilot"),
        ("WorkBuddy", ".workbuddy/mcp.json", "WorkBuddy", "workbuddy"),
        ("WorkBuddy AI", ".workbuddy-ai/mcp.json", "WorkBuddy AI", "workbuddy-ai"),
        ("CodeBuddy", ".codebuddy/mcp.json", "VS Code", "vscode"),
        ("Claude Desktop", "AppData/Roaming/Claude/claude_desktop_config.json",
         "Claude Desktop", "claude-desktop"),
        ("Claude Desktop 3p", "AppData/Roaming/Claude-3p/claude_desktop_config.json",
         "Claude Desktop", "claude-desktop"),
        ("VS Code", "AppData/Roaming/Code/User/mcp.json", "VS Code", "vscode"),
    ):
        yield label, home / rel, host, manager_client, (
            patch_toml if rel.endswith(".toml") else patch_json)
    for profile in ("desktop", "web"):
        yield (f"DSH {profile}", home / f".dsh/profiles/{profile}/cordis.patch.yml",
               "DSH", "dsh", patch_dsh)
    for package in sorted((home / "AppData/Local/Packages").glob("*Claude*")):
        for app in ("Claude", "Claude-3p"):
            path = package / f"LocalCache/Roaming/{app}/claude_desktop_config.json"
            if path.is_file():
                yield "Claude Desktop Store", path, "Claude Desktop", "claude-desktop", patch_json


def semantically_changed(original: str, updated: str, path: Path, patcher) -> bool:
    """Ignore serialization-only rewrites so the audit does not ask for needless writes."""
    if patcher in (patch_json, patch_library) or path.suffix.casefold() == ".json":
        return json.loads(updated) != json.loads(original)
    if path.suffix.casefold() == ".toml":
        return tomllib.loads(updated) != tomllib.loads(original)
    if path.suffix.casefold() in (".yml", ".yaml"):
        import yaml  # Optional audit-tool dependency; not a runtime dependency.
        return yaml.safe_load(updated) != yaml.safe_load(original)
    return updated.strip() != original.strip()


def run(home, apply=False, backup=None):
    report = []
    for index, (label, path, host, manager_client, patcher) in enumerate(targets(home)):
        manager = magpie_state(home, manager_client) if manager_client else {
            "managed": False, "error": False}
        item = {"client": label, "path": str(path), "exists": path.is_file(),
                "manager": "magpie" if manager["managed"] else "nijika"}
        report.append(item)
        if manager["error"]:
            item["error"] = "MAGPIE ownership state is unreadable"
            continue
        if manager["managed"]:
            item["skipped"] = "MAGPIE managed; use the manager instead of direct edits"
            continue
        if not path.is_file():
            continue
        original = path.read_bytes()
        text = original.decode("utf-8-sig")
        try:
            updated, fragments = patcher(text) if patcher == patch_library else patcher(text, host)
            item["nijika_scopes"] = len(fragments)
            item["aliases_before"] = [
                list(v["before"]) if isinstance(v["before"], dict) else
                [x.get("name", x.get("insert", [{}])[0].get("id", "")) for x in v["before"]]
                for v in fragments]
            item["changed"] = bool(fragments) and semantically_changed(text, updated, path, patcher)
            if apply and item["changed"]:
                # Back up public Nijika fragments only; reject surprise secrets
                # rather than copying full credential-bearing client files.
                def check(value):
                    if isinstance(value, dict):
                        for key, val in value.items():
                            if key == "env" and any(k not in {"NIJIKA_AGENT_NAME", "NIJIKA_HOST_NAME"} for k in val):
                                raise ValueError("unexpected Nijika env: manual review required")
                            check(val)
                    elif isinstance(value, list):
                        for val in value:
                            check(val)
                check(fragments)
                backup.mkdir(parents=True, exist_ok=True)
                (backup / f"{index:02d}-nijika-fragments.json").write_text(json.dumps(
                    {"path": str(path), "sha256_before": hashlib.sha256(original).hexdigest(),
                     "fragments": fragments}, ensure_ascii=False, indent=2), encoding="utf-8")
                if path.read_bytes() != original:
                    raise ValueError("concurrent config change; refused write")
                with path.open("w", encoding="utf-8", newline="") as out:
                    out.write(updated)
                item["applied"] = True
                item["sha256_after"] = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception as error:
            # Errors never echo parsed content, tokens or source lines.
            item["error"] = type(error).__name__
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires --backup")
    report = run(args.home, args.apply, args.backup)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    if any("error" in item for item in report):
        raise SystemExit(1)
