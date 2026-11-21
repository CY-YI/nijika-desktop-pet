"""A native multiline edit control inside the desktop notification bubble."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                  wintypes.DWORD, *([ctypes.c_int] * 4), wintypes.HWND,
                                  wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.MoveWindow.argtypes = [wintypes.HWND, *([ctypes.c_int] * 4), wintypes.BOOL]
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
gdi32.CreateSolidBrush.argtypes = [wintypes.DWORD]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.CreateFontW.argtypes = [*([ctypes.c_int] * 13), wintypes.LPCWSTR]
gdi32.CreateFontW.restype = wintypes.HFONT
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.DWORD]
gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.DWORD]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]

EDIT_RGB = (255, 253, 246)
_EDIT_BACKGROUND = EDIT_RGB[0] | (EDIT_RGB[1] << 8) | (EDIT_RGB[2] << 16)
_EDIT_TEXT = 0x363841  # BGR used by GDI


def copy_reply_reference(owner: int, request_id: str) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
    kernel32.GlobalFree.restype = wintypes.HANDLE
    data = (f"请读取虹夏桌面回复（request_id={request_id}）。\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    if not handle:
        return False
    try:
        allocation = kernel32.GlobalLock(handle)
        if not allocation:
            return False
        ctypes.memmove(allocation, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(owner):
            return False
        try:
            if not user32.EmptyClipboard() or not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
                return False
            handle = None  # Windows now owns the allocation.
            return True
        finally:
            user32.CloseClipboard()
    finally:
        if handle:
            kernel32.GlobalFree(handle)


class InlineReply:
    def __init__(self):
        self.hwnd = None
        self.font = None
        self.brush = None

    def place(self, parent: int, rect: tuple[int, int, int, int], draft: str) -> None:
        left, top, right, bottom = rect
        if self.hwnd:
            user32.MoveWindow(self.hwnd, left, top, right - left, bottom - top, True)
            return
        if not self.font:
            self.font = gdi32.CreateFontW(-20, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Microsoft YaHei UI")
        if not self.brush:
            self.brush = gdi32.CreateSolidBrush(_EDIT_BACKGROUND)
        # WS_CHILD | WS_VISIBLE | ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN
        self.hwnd = user32.CreateWindowExW(0, "EDIT", draft, 0x50001044, left, top,
                                          right - left, bottom - top, parent, None, None, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        if self.font:
            user32.SendMessageW(self.hwnd, 0x0030, self.font, 1)  # WM_SETFONT
        user32.SendMessageW(self.hwnd, 0x00B1, len(draft), len(draft))  # EM_SETSEL

    def focus(self, parent: int) -> None:
        if self.hwnd:
            user32.SetForegroundWindow(parent)
            user32.SetFocus(self.hwnd)

    def text(self) -> str:
        if not self.hwnd:
            return ""
        buffer = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(self.hwnd) + 1)
        user32.GetWindowTextW(self.hwnd, buffer, len(buffer))
        return buffer.value

    def paint(self, dc: int) -> int:
        gdi32.SetTextColor(dc, _EDIT_TEXT)
        gdi32.SetBkColor(dc, _EDIT_BACKGROUND)
        return self.brush or 0

    def key_action(self, message: wintypes.MSG) -> str | None:
        if self.hwnd and message.hWnd == self.hwnd and message.message == 0x0100:
            if message.wParam == 0x1B:
                return "collapse"
            if message.wParam == 0x0D and user32.GetKeyState(0x11) < 0:
                return "send"
        return None

    def hide(self) -> None:
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def close(self) -> None:
        self.hide()
        for resource in (self.font, self.brush):
            if resource:
                gdi32.DeleteObject(resource)
        self.font = self.brush = None
