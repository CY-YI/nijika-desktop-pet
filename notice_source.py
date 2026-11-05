"""Display-only Agent and host identity, shared by MCP, hooks and renderer."""
from __future__ import annotations

from dataclasses import dataclass
import re


# These describe products, not the underlying LLM/model or authentication.
HOSTS = {
    "codex": ("ChatGPT", "Codex"), "codex-mcp-client": ("ChatGPT", "Codex"),
    "work": ("ChatGPT", "Work"), "chatgpt work": ("ChatGPT", "Work"),
    "claude-code": ("Claude", "Claude Code"), "claude code": ("Claude", "Claude Code"),
    "claude-desktop": ("Claude", "Claude Desktop"), "claude desktop": ("Claude", "Claude Desktop"),
    "dsh": ("Agent", "DSH"), "deepseek harness": ("Agent", "DSH"),
    "deepseek-harness": ("Agent", "DSH"), "@deepseek-ai/dsh-mcp-client": ("Agent", "DSH"),
    # Actual initialize.clientInfo.name in the installed DSH desktop bridge.
    # The npm package name above is a separate legacy alias.
    "dsh-mcp-client": ("Agent", "DSH"),
    "gemini": ("Gemini", "Gemini CLI"), "gemini-cli": ("Gemini", "Gemini CLI"),
    "gemini cli": ("Gemini", "Gemini CLI"),
    "copilot": ("Copilot", "Copilot CLI"), "copilot-cli": ("Copilot", "Copilot CLI"),
    "copilot cli": ("Copilot", "Copilot CLI"), "github-copilot": ("Copilot", "Copilot CLI"),
    "workbuddy": ("Agent", "WorkBuddy"), "workbuddy-ai": ("Agent", "WorkBuddy AI"),
    "workbuddy ai": ("Agent", "WorkBuddy AI"),
    "vscode": ("Agent", "VS Code"), "vs code": ("Agent", "VS Code"),
    "obsidian": ("Agent", "Obsidian"),
}
GENERIC = {"", "auto", "agent"}
MULTIMODEL_SOFTWARE = {"dsh", "workbuddy", "workbuddy ai"}
HOST_PRODUCT_LABELS = {
    "chatgpt", "chatgpt work", "codex", "work", "dsh", "deepseek harness",
    "claude code", "claude desktop", "workbuddy", "workbuddy ai",
    "vs code", "vs code insiders", "obsidian",
}


@dataclass(frozen=True)
class NoticeSource:
    agent: str
    software: str

    @property
    def heading(self) -> str:
        if self.software.casefold() in {"vs code", "vs code insiders"}:
            return f"{self.software} · {self.agent}" if self.agent else self.software
        return f"{self.agent} · {self.software}" if self.software else self.agent


def _safe_agent_for_host(agent: str, software: str) -> str:
    """Do not present a host/engine product as the Agent of a cloud multimodel host."""
    if software.casefold() in MULTIMODEL_SOFTWARE and agent.casefold() in HOST_PRODUCT_LABELS:
        return "Agent"
    return agent or "Agent"


def clean(value: str | None, maximum: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value.strip()) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError(f"source must be a single printable line of at most {maximum} characters")
    return value.strip()


def resolve_source(configured: str = "auto", host: str = "", caller: str = "",
                   agent_name: str | None = None, software: str | None = None) -> NoticeSource:
    """Known handshakes repair stale legacy labels; explicit metadata adds detail.

    Work and editor integrations can share an engine handshake. Explicit host
    configuration is needed there. Unknown/multimodel hosts never imply a model.
    All fields remain presentation metadata and convey no authority.
    """
    configured, host = clean(configured, 20), clean(host, 40)
    agent_name, software = clean(agent_name, 20), clean(software, 40)
    known = HOSTS.get(caller.strip().casefold())
    legacy = HOSTS.get(configured.casefold())
    if host or software:
        selected_host = software or host
        defaults = HOSTS.get(selected_host.casefold())
        # New explicit agent labels are preserved; a legacy product name is not
        # mistaken for the Agent name.
        agent = agent_name or (configured if configured.casefold() not in GENERIC and not legacy else "")
        software_value = defaults[1] if defaults else selected_host
        return NoticeSource(_safe_agent_for_host(agent or (defaults[0] if defaults else "Agent"),
                                                 software_value), software_value)
    if known:
        if configured.casefold() in {"work", "chatgpt work"} and known[1] == "Codex":
            known = HOSTS["work"]
        custom = configured if configured.casefold() not in GENERIC and not legacy else ""
        return NoticeSource(_safe_agent_for_host(agent_name or custom or known[0], known[1]), known[1])
    if legacy:
        # No trustworthy caller: retain a legacy host label, without guessing
        # that DSH/WorkBuddy is necessarily running DeepSeek.
        return NoticeSource(_safe_agent_for_host(agent_name or legacy[0], legacy[1]), legacy[1])
    agent = agent_name or (configured if configured.casefold() not in GENERIC else "Agent")
    return NoticeSource(_safe_agent_for_host(agent, "未识别软件"), "未识别软件")


def notification_source(agent: str, software: str = "") -> NoticeSource:
    """Old rows remain readable without rewriting user history."""
    return NoticeSource(agent, software) if software else resolve_source(agent)


def task_heading(title: str, source: NoticeSource) -> str:
    """Remove only leading delimited identity prefixes; preserve task prose."""
    aliases = {source.agent, source.software, source.heading}
    aliases.update(key for key, value in HOSTS.items()
                   if value[1].casefold() == source.software.casefold())
    for _ in range(4):
        for prefix in sorted(aliases, key=len, reverse=True):
            if not prefix:
                continue
            match = re.match(re.escape(prefix) + r"\s*[·•:：|/]\s*", title, re.IGNORECASE)
            if match and title[match.end():].strip():
                title = title[match.end():].strip()
                break
        else:
            break
    return title
