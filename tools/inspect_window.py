"""Capture the actual desktop-pet window and optionally exercise its click handler."""

import argparse
import ctypes
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab


user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except AttributeError:
    user32.SetProcessDPIAware()
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def print_window(window: int, rect: wintypes.RECT) -> Image.Image:
    width, height = rect.right - rect.left, rect.bottom - rect.top
    screen = user32.GetWindowDC(window)
    memory = gdi32.CreateCompatibleDC(screen)
    bitmap = gdi32.CreateCompatibleBitmap(screen, width, height)
    old = gdi32.SelectObject(memory, bitmap)
    try:
        if not user32.PrintWindow(window, memory, 2):
            raise ctypes.WinError(ctypes.get_last_error())
        header = BITMAPINFOHEADER()
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = width
        header.biHeight = -height
        header.biPlanes = 1
        header.biBitCount = 32
        pixels = ctypes.create_string_buffer(width * height * 4)
        if not gdi32.GetDIBits(memory, bitmap, 0, height, pixels, ctypes.byref(header), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1).copy()
    finally:
        gdi32.SelectObject(memory, old)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(window, screen)

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path, nargs="?")
parser.add_argument("--click", action="store_true")
parser.add_argument("--after-click-ms", type=int, default=350)
parser.add_argument("--drag", nargs=2, type=int, metavar=("DX", "DY"))
parser.add_argument("--close", action="store_true")
args = parser.parse_args()

window = user32.FindWindowW("NijikaDesktopPetWindow", None)
if not window or not user32.IsWindowVisible(window):
    raise SystemExit("Desktop-pet window is not visible")
rect = wintypes.RECT()
if not user32.GetWindowRect(window, ctypes.byref(rect)):
    raise ctypes.WinError(ctypes.get_last_error())
print(f"visible=1 rect=({rect.left},{rect.top},{rect.right},{rect.bottom})", flush=True)

if args.click:
    x = (rect.right - rect.left) // 2
    y = (rect.bottom - rect.top) // 3
    lparam = x | (y << 16)
    user32.SendMessageW(window, 0x0201, 1, lparam)
    user32.SendMessageW(window, 0x0202, 0, lparam)
    time.sleep(max(0, args.after_click_ms) / 1000)

if args.drag:
    start = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(start))
    cx = rect.left + (rect.right - rect.left) // 2
    cy = rect.top + (rect.bottom - rect.top) // 3
    user32.SetCursorPos(cx, cy)
    user32.SendMessageW(window, 0x0201, 1, 0)
    user32.SetCursorPos(cx + args.drag[0], cy + args.drag[1])
    user32.SendMessageW(window, 0x0200, 1, 0)
    user32.SendMessageW(window, 0x0202, 0, 0)
    user32.SetCursorPos(start.x, start.y)
    user32.GetWindowRect(window, ctypes.byref(rect))
    print(f"after_drag_rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")

title = ctypes.create_unicode_buffer(200)
user32.GetWindowTextW(window, title, len(title))
print(f"title={title.value.encode('unicode_escape').decode('ascii')}")

if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        image = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
        method = "screen"
    except OSError:
        image = print_window(window, rect)
        method = "PrintWindow"
    image.save(args.output)
    print(f"image={args.output} method={method}")

if args.close:
    user32.SendMessageW(window, 0x0010, 0, 0)
