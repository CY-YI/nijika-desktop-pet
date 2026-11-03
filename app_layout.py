"""Stable paths shared by the application and maintenance tools."""

from __future__ import annotations

from pathlib import Path


MCP_DIRECTORY_NAME = "虹夏MCP-v2"
MCP_EXECUTABLE_NAME = "虹夏MCP-v2.exe"


def bundled_mcp_path(application_root: Path) -> Path:
    """Return the current onedir MCP executable for an application root."""
    return application_root / "dist" / MCP_DIRECTORY_NAME / MCP_EXECUTABLE_NAME


def legacy_bundled_mcp_path(application_root: Path) -> Path:
    """Return the pre-0.1.9 onefile path used only for safe migration."""
    return application_root / "dist" / MCP_EXECUTABLE_NAME
