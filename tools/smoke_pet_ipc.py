"""Release smoke test: packaged MCP request -> visible pet bubble -> clicked reply."""

from __future__ import annotations

import asyncio
import argparse
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pet import BubbleNotice, WINDOW_CLASS, render_bubble  # noqa: E402
from notification_store import NotificationStore  # noqa: E402

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    if not user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
        user32.SetProcessDPIAware()
except AttributeError:
    user32.SetProcessDPIAware()
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t


def visible_window(class_name: str, expected_size: tuple[int, int] | None = None) -> int | None:
    window = user32.FindWindowW(class_name, None)
    if not window or not user32.IsWindowVisible(window):
        return None
    if expected_size:
        rect = wintypes.RECT()
        if not user32.GetWindowRect(window, ctypes.byref(rect)):
            return None
        if (rect.right - rect.left, rect.bottom - rect.top) != expected_size:
            return None
    return window


async def until_window(class_name: str, size: tuple[int, int] | None = None) -> int:
    deadline = time.monotonic() + 18.0
    last = "missing"
    while time.monotonic() < deadline:
        window = visible_window(class_name, size)
        if window:
            return window
        raw_window = user32.FindWindowW(class_name, None)
        if raw_window:
            rect = wintypes.RECT()
            user32.GetWindowRect(raw_window, ctypes.byref(rect))
            last = (f"hwnd={raw_window} visible={bool(user32.IsWindowVisible(raw_window))} "
                    f"size=({rect.right - rect.left},{rect.bottom - rect.top})")
        await asyncio.sleep(0.1)
    raise AssertionError(f"Visible window did not appear: {class_name}, size={size}; last={last}")


async def main(source: bool) -> None:
    if visible_window(WINDOW_CLASS):
        raise SystemExit("Close the already running desktop pet before this isolated smoke test")
    pet_exe = ROOT / "dist" / "虹夏桌宠.exe"
    mcp_exe = ROOT / "dist" / "虹夏MCP-v2" / "虹夏MCP-v2.exe"
    if not source and (not pet_exe.is_file() or not mcp_exe.is_file()):
        raise SystemExit("Run build.ps1 before the packaged smoke test")
    pet_command = ([sys.executable, str(ROOT / "pet.py")] if source
                   else [str(pet_exe)])
    mcp_command = sys.executable if source else str(mcp_exe)
    mcp_args = [str(ROOT / "mcp_server.py")] if source else []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notifications.sqlite3"
        environment = os.environ.copy()
        environment["NIJIKA_PET_DB_PATH"] = str(path)
        process = subprocess.Popen(pet_command, env=environment)
        try:
            await until_window(WINDOW_CLASS)
            params = StdioServerParameters(command=mcp_command, args=mcp_args,
                                           env=environment)
            async with Client(params) as client:
                question = "发布说明：双击虹夏桌宠即可看到坐姿角色。Codex 的选择题可在气泡中直接回答。接受这段说明吗？"
                created = await client.call_tool(
                    "request_decision",
                    {"task": "文案审阅", "question": question, "options": [
                        {"label": "接受文案", "description": "采用这段文案，无需回到聊天确认。"},
                        {"label": "需要修改", "description": "暂不定稿，后续再说明修改要求。"},
                    ]},
                )
                assert not created.is_error and created.structured_content
                request_id = created.structured_content["request_id"]
                assert NotificationStore(path).get(request_id).status == "pending"
                image, actions, _ = render_bubble(
                    BubbleNotice(
                        "Codex · 文案审阅", question,
                        actions=("接受文案", "需要修改"),
                        action_descriptions=(
                            "采用这段文案，无需回到聊天确认。",
                            "暂不定稿，后续再说明修改要求。",
                        ),
                        kind="agent", duration=None, request_id=request_id,
                    )
                )
                bubble = await until_window("NijikaDesktopPetBubbleWindow", image.size)
                left, top, right, bottom = actions[0]
                x, y = (left + right) // 2, (top + bottom) // 2
                user32.SendMessageW(bubble, 0x0202, 0, x | (y << 16))
                result = await client.call_tool(
                    "wait_for_reply", {"request_id": request_id, "timeout_seconds": 5}
                )
                assert result.structured_content["status"] == "answered", result
                assert result.structured_content["choice"] == "接受文案", result
                assert NotificationStore(path).next_pending() is None
        finally:
            window = visible_window(WINDOW_CLASS)
            if window:
                user32.SendMessageW(window, 0x0010, 0, 0)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
    mode = "Source" if source else "Packaged"
    print(f"{mode} MCP -> visible desktop bubble -> user choice -> MCP reply: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="store_true", help="run source entrypoints")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.source))
