"""Stable paths shared by the application and maintenance tools."""

from __future__ import annotations

from pathlib import Path


MCP_DIRECTORY_NAME = "虹夏MCP-v2"
MCP_EXECUTABLE_NAME = "虹夏MCP-v2.exe"


def bundled_mcp_path(application_root: Path) -> Path:
    """Return the current onedir MCP executable for an application root."""
    return application_root / "dist" / MCP_DIRECTORY_NAME / MCP_EXECUTABLE_NAME


def validate_bundled_mcp(application_root: Path) -> Path:
    """Return the MCP executable only when its onedir runtime is complete."""
    executable = bundled_mcp_path(application_root)
    runtime = executable.parent / "_internal"
    if not executable.is_file() or not runtime.is_dir():
        raise ValueError(
            "虹夏 MCP 安装不完整。必须同时保留 "
            f"{MCP_DIRECTORY_NAME}\\{MCP_EXECUTABLE_NAME} 和同目录的 _internal；"
            "不能只复制 EXE。"
        )
    return executable


def legacy_bundled_mcp_path(application_root: Path) -> Path:
    """Return the pre-0.1.9 onefile path used only for safe migration."""
    return application_root / "dist" / MCP_EXECUTABLE_NAME
