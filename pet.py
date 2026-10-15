"""A small, per-pixel-transparent Windows desktop companion."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageDraw

from notification_store import Notification, NotificationStore
from legacy_queue import LegacyQueueBridge, legacy_database_paths
from control_store import ControlStore, DEFAULTS
from companion_store import CompanionStore


EXPRESSIONS = (
    "curious", "happy", "worried", "sleepy", "wink", "thinking", "pout", "excited"
)
SPRITE_NAMES = (*EXPRESSIONS, "blink")
LABELS = {
    "curious": "好奇", "happy": "开心", "worried": "求助", "sleepy": "安睡",
    "wink": "眨眼俏皮", "thinking": "思考", "pout": "小生气", "excited": "加油",
}
WINDOW_CLASS = "NijikaDesktopPetWindow"
ERROR_CLASS_ALREADY_EXISTS = 1410
WIDTHS = (260, 320, 380)


def log_notice_event(event: str, detail: str = "") -> None:
    """Keep a small local diagnostic trail for queue/display failures."""
    directory = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    try:
        with (directory / "nijika-notice.log").open("a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {event} {detail}\n")
    except OSError:
        pass

if sys.platform != "win32":
    raise SystemExit("This desktop pet currently supports Windows only.")

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
winmm = ctypes.WinDLL("winmm", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.DefWindowProcW.restype = LRESULT
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(SIZE), wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    wintypes.DWORD, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
user32.GetMessageW.restype = ctypes.c_int
user32.SetTimer.argtypes = [
    wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p
]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.SetWindowTextW.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
user32.MonitorFromRect.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.SystemParametersInfoW.argtypes = [
    wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT
]
user32.SystemParametersInfoW.restype = wintypes.BOOL
user32.AppendMenuW.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR
]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, wintypes.HWND, ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
winmm.timeBeginPeriod.restype = wintypes.UINT
winmm.timeEndPeriod.argtypes = [wintypes.UINT]
winmm.timeEndPeriod.restype = wintypes.UINT

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
CS_DBLCLKS = 0x0008
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
ULW_ALPHA = 0x00000002
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_MOUSEMOVE = 0x0200
WM_TIMER = 0x0113
MK_LBUTTON = 0x0001
MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
MF_CHECKED = 0x0008
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
SPI_GETWORKAREA = 0x0030


def monitor_work_area(anchor: tuple[int, int, int, int]) -> wintypes.RECT:
    x, y, width, height = anchor
    rect = wintypes.RECT(x, y, x + width, y + height)
    monitor = user32.MonitorFromRect(ctypes.byref(rect), 2)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return info.rcWork
    work = wintypes.RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work), 0)
    return work


def resource_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "sprites"


def sprite_metrics() -> dict[str, tuple[int, int, int, int]]:
    metrics = {}
    expected = None
    for name in SPRITE_NAMES:
        path = resource_dir() / f"{name}.png"
        with Image.open(path) as image:
            if image.mode != "RGBA":
                raise ValueError(f"{path.name} must be RGBA")
            if expected is None:
                expected = image.size
            elif image.size != expected:
                raise ValueError(f"{path.name} has a different canvas size")
            alpha = image.getchannel("A")
            box = alpha.getbbox()
            if box is None or alpha.getpixel((0, 0)) != 0:
                raise ValueError(f"{path.name} has no valid transparent character")
            metrics[name] = box
    return metrics


def premultiplied_bgra(image: Image.Image) -> bytes:
    # Pillow performs alpha multiplication in native code; Win32 expects BGRA.
    red, green, blue, alpha = image.convert("RGBa").split()
    return Image.merge("RGBA", (blue, green, red, alpha)).tobytes()


def draw_star(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int, opacity: float) -> None:
    points = [
        (x, y - radius), (x + radius // 3, y - radius // 3),
        (x + radius, y), (x + radius // 3, y + radius // 3),
        (x, y + radius), (x - radius // 3, y + radius // 3),
        (x - radius, y), (x - radius // 3, y - radius // 3),
    ]
    draw.polygon(points, fill=(255, 232, 124, round(235 * opacity)))
    draw.line(
        points + [points[0]], fill=(104, 66, 44, round(240 * opacity)),
        width=max(1, radius // 6),
    )


def format_countdown(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def draw_focus_badge(image: Image.Image, text: str, *, mode: str) -> None:
    """Paint a small timer chip above the character's hair."""
    draw = ImageDraw.Draw(image, "RGBA")
    font = bubble_font(max(15, image.width // 20), bold=True)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_width = probe.textlength(text, font=font)
    width = int(text_width) + 34
    height = int(font.size) + 16
    # Top-right corner stays transparent for every pose, so the chip never hides the face.
    left = max(4, image.width - width - 8)
    top = max(2, int(image.height * 0.012))
    fill = (255, 244, 214, 243) if mode == "focus" else (223, 244, 226, 243)
    outline = (196, 132, 96, 255) if mode == "focus" else (104, 156, 108, 255)
    draw.rounded_rectangle((left, top, left + width, top + height), radius=height // 2,
                           fill=fill, outline=outline, width=2)
    draw.text((left + 17, top + 5), text, font=font,
              fill=(126, 78, 60, 255) if mode == "focus" else (52, 104, 60, 255))


def render_pose(
    source: Image.Image, *, shift_x: float = 0.0, shift_y: float = 0.0,
    angle: float = 0.0, scale_x: float = 1.0, scale_y: float = 1.0,
    sparkle: float = 0.0,
) -> Image.Image:
    """Sample the art at subpixel positions so animation does not jump between poses."""
    width, height = source.size
    if not (shift_x or shift_y or angle or scale_x != 1.0 or scale_y != 1.0):
        canvas = source.copy()
    else:
        theta = math.radians(angle)
        sine, cosine = math.sin(theta), math.cos(theta)
        cx, cy = width / 2, height * 0.78
        a, b = cosine / scale_x, sine / scale_x
        d, e = -sine / scale_y, cosine / scale_y
        c = cx - a * (cx + shift_x) - b * (cy + shift_y)
        f = cy - d * (cx + shift_x) - e * (cy + shift_y)
        canvas = source.transform(
            source.size, Image.Transform.AFFINE, (a, b, c, d, e, f),
            resample=Image.Resampling.BILINEAR, fillcolor=(0, 0, 0, 0),
        )
    if sparkle > 0.01:
        draw = ImageDraw.Draw(canvas, "RGBA")
        draw_star(draw, int(width * 0.11), int(height * 0.21), max(9, width // 22), sparkle)
        draw_star(draw, int(width * 0.88), int(height * 0.32), max(8, width // 27), sparkle)
        draw_star(draw, int(width * 0.17), int(height * 0.39), max(5, width // 42), sparkle)
    return canvas


class SpriteSet:
    def __init__(self, width: int, height: int, directory: Path | None = None):
        self.width = width
        self.height = height
        self.sources: dict[str, Image.Image] = {}
        self.memory_dc = None
        self.bitmap = None
        self.old_bitmap = None
        self.bits = ctypes.c_void_p()
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            for name in SPRITE_NAMES:
                with Image.open((directory or resource_dir()) / f"{name}.png") as source:
                    art = source.convert("RGBA").resize(
                        (width - 20, height - 30), Image.Resampling.LANCZOS
                    )
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                canvas.alpha_composite(art, (10, 20))
                self.sources[name] = canvas
            header = BITMAPINFOHEADER()
            header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            header.biWidth = width
            header.biHeight = -height  # top-down DIB
            header.biPlanes = 1
            header.biBitCount = 32
            self.bitmap = gdi32.CreateDIBSection(
                screen_dc, ctypes.byref(header), 0, ctypes.byref(self.bits), None, 0
            )
            if not self.bitmap or not self.bits.value:
                raise ctypes.WinError(ctypes.get_last_error())
            self.memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not self.memory_dc:
                raise ctypes.WinError(ctypes.get_last_error())
            self.old_bitmap = gdi32.SelectObject(self.memory_dc, self.bitmap)
            if not self.old_bitmap:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close()
            raise
        finally:
            user32.ReleaseDC(None, screen_dc)

    def close(self) -> None:
        if self.memory_dc:
            if self.old_bitmap:
                gdi32.SelectObject(self.memory_dc, self.old_bitmap)
            gdi32.DeleteDC(self.memory_dc)
            self.memory_dc = None
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
            self.bitmap = None
        self.sources.clear()

    def render(self, name: str, badge: tuple[str, str] | None = None, **pose: float) -> None:
        image = render_pose(self.sources[name], **pose)
        if badge:
            draw_focus_badge(image, badge[0], mode=badge[1])
        raw = premultiplied_bgra(image)
        ctypes.memmove(self.bits, raw, len(raw))


from dataclasses import dataclass
from PIL import ImageFont


@dataclass(frozen=True)
class BubbleNotice:
    title: str
    text: str
    actions: tuple[str, ...] = ()
    action_descriptions: tuple[str, ...] = ()
    action_recommended: tuple[bool, ...] = ()
    kind: str = "chat"
    duration: float | None = 6.0
    request_id: str | None = None


def bubble_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def wrap_bubble_text(text: str, font: ImageFont.FreeTypeFont, width: int,
                     limit: int | None = 3) -> list[str]:
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines: list[str] = []
    for paragraph in text.replace("\r", "").split("\n"):
        current = ""
        for char in paragraph:
            if current and probe.textlength(current + char, font=font) > width:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    if limit is not None and len(lines) > limit:
        lines = lines[:limit]
        while lines[-1] and probe.textlength(lines[-1] + "…", font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines or [""]


def fit_bubble_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if probe.textlength(text, font=font) <= width:
        return text
    while text and probe.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"


def render_bubble(notice: BubbleNotice, width: int = 430) -> tuple[Image.Image, list[tuple[int, int, int, int]], tuple[int, int, int, int]]:
    title_font = bubble_font(21, bold=True)
    body_font = bubble_font(24)
    small_font = bubble_font(17)
    button_font = bubble_font(21, bold=True)
    description_font = bubble_font(16)
    described = (len(notice.action_descriptions) == len(notice.actions)
                 and any(notice.action_descriptions))
    lines = wrap_bubble_text(notice.text, body_font, width - 58,
                             limit=None if notice.request_id and described else
                             6 if notice.request_id else 3)
    text_y = 62
    content_bottom = text_y + len(lines) * 33
    footer_y = None
    if notice.kind in ("agent", "approval"):
        footer_y = content_bottom + 7
        content_bottom = footer_y + 25
    button_y = content_bottom + 9 if notice.actions else None
    option_lines = (
        [wrap_bubble_text(description, description_font, width - 90, limit=3)
         for description in notice.action_descriptions[:3]]
        if described else []
    )
    option_heights = [max(76, 57 + 19 * (len(lines) - 1))
                      for lines in option_lines]
    if button_y is not None and described:
        card_bottom = button_y + sum(option_heights) + (len(option_heights) - 1) * 8 + 17
    elif button_y is not None:
        card_bottom = button_y + 45 + 18
    else:
        card_bottom = content_bottom + 17
    height = card_bottom + 20
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    outline = (111, 81, 66, 255) if notice.kind == "agent" else (119, 89, 76, 255)
    fill = (255, 249, 232, 250) if notice.kind == "agent" else (255, 253, 247, 250)
    draw.rounded_rectangle((9, 9, width - 4, card_bottom + 3), radius=24, fill=(67, 49, 39, 55))
    draw.rounded_rectangle((5, 5, width - 9, card_bottom), radius=24, fill=fill, outline=outline, width=3)
    pointer_x = width // 2
    draw.polygon(
        ((pointer_x - 16, card_bottom - 2), (pointer_x + 17, card_bottom - 2), (pointer_x + 1, height - 5)),
        fill=fill, outline=outline,
    )
    draw.line((pointer_x - 13, card_bottom - 2, pointer_x + 14, card_bottom - 2), fill=fill, width=5)
    draw.text((27, 22), fit_bubble_text(notice.title, title_font, width - 95),
              font=title_font, fill=(149, 80, 65, 255))
    draw.text((width - 40, 17), "×", font=title_font, fill=(130, 117, 110, 255))
    for index, line in enumerate(lines):
        draw.text((27, text_y + index * 33), line, font=body_font, fill=(65, 56, 55, 255))
    if footer_y is not None:
        footer = ("审批提醒 · 气泡点击不会授权命令" if notice.kind == "approval"
                  else "点击选项后，Agent 会按你的决定继续" if notice.request_id and described
                  else "完成提醒 · 点击仅确认收到" if notice.request_id
                  else "本地演示 · 未连接 Agent")
        draw.text((27, footer_y), footer, font=small_font, fill=(123, 108, 98, 255))
    action_rects: list[tuple[int, int, int, int]] = []
    if button_y is not None:
        actions = notice.actions[:3]
        if described:
            top = button_y
            for index, label in enumerate(actions):
                rect = (27, top, width - 27, top + option_heights[index])
                recommended = (index < len(notice.action_recommended)
                               and notice.action_recommended[index])
                draw.rounded_rectangle(rect, radius=13,
                                       fill=(255, 218, 146, 255) if recommended else (255, 232, 185, 255),
                                       outline=(143, 97, 76, 255), width=2)
                if recommended:
                    draw.text((width - 95, top + 11), "推荐", font=small_font,
                              fill=(161, 77, 57, 255))
                draw.text((42, top + 8), fit_bubble_text(label, button_font,
                          width - (170 if recommended else 95)),
                          font=button_font, fill=(88, 62, 54, 255))
                for line_index, line in enumerate(option_lines[index]):
                    draw.text((43, top + 36 + line_index * 19), line,
                              font=description_font, fill=(105, 82, 72, 255))
                action_rects.append(rect)
                top += option_heights[index] + 8
        else:
            gap = 11
            button_width = (width - 54 - gap * (len(actions) - 1)) // len(actions)
            for index, label in enumerate(actions):
                left = 27 + index * (button_width + gap)
                rect = (left, button_y, left + button_width, button_y + 44)
                draw.rounded_rectangle(rect, radius=13, fill=(255, 222, 153, 255), outline=(143, 97, 76, 255), width=2)
                bbox = draw.textbbox((0, 0), label, font=button_font)
                text_width = bbox[2] - bbox[0]
                draw.text((left + (button_width - text_width) / 2, button_y + 7), label, font=button_font, fill=(88, 62, 54, 255))
                action_rects.append(rect)
    return canvas, action_rects, (width - 52, 10, width - 13, 50)


class BubbleOverlay:
    CLASS_NAME = "NijikaDesktopPetBubbleWindow"

    def __init__(self, on_action, on_close):
        self.on_action = on_action
        self.on_close = on_close
        self.hwnd: int | None = None
        self.owner: int | None = None
        self.notice: BubbleNotice | None = None
        self.expires_at: float | None = None
        self.width = self.height = 0
        self.action_rects: list[tuple[int, int, int, int]] = []
        self.close_rect = (0, 0, 0, 0)
        self.anchor = (0, 0, 0, 0)
        self.memory_dc = self.bitmap = self.old_bitmap = None
        self.bits = ctypes.c_void_p()
        self._callback = WNDPROC(self._wnd_proc)

    def _ensure_window(self) -> None:
        if self.hwnd and user32.IsWindow(self.hwnd):
            return
        self.hwnd = None
        module = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSW()
        window_class.style = CS_DBLCLKS
        window_class.lpfnWndProc = self._callback
        window_class.hInstance = module
        window_class.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))
        window_class.lpszClassName = self.CLASS_NAME
        if not user32.RegisterClassW(ctypes.byref(window_class)):
            error = ctypes.get_last_error()
            if error != ERROR_CLASS_ALREADY_EXISTS:
                raise ctypes.WinError(error)
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            self.CLASS_NAME, "虹夏消息气泡", WS_POPUP,
            0, 0, 1, 1, self.owner, None, module, None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

    def _release_surface(self) -> None:
        if self.memory_dc:
            if self.old_bitmap:
                gdi32.SelectObject(self.memory_dc, self.old_bitmap)
            gdi32.DeleteDC(self.memory_dc)
            self.memory_dc = None
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
            self.bitmap = None
        self.old_bitmap = None

    def _load_surface(self, image: Image.Image) -> None:
        self._release_surface()
        self.width, self.height = image.size
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            header = BITMAPINFOHEADER()
            header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            header.biWidth = self.width
            header.biHeight = -self.height
            header.biPlanes = 1
            header.biBitCount = 32
            self.bits = ctypes.c_void_p()
            self.bitmap = gdi32.CreateDIBSection(
                screen_dc, ctypes.byref(header), 0, ctypes.byref(self.bits), None, 0
            )
            if not self.bitmap or not self.bits.value:
                raise ctypes.WinError(ctypes.get_last_error())
            self.memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not self.memory_dc:
                raise ctypes.WinError(ctypes.get_last_error())
            self.old_bitmap = gdi32.SelectObject(self.memory_dc, self.bitmap)
            if not self.old_bitmap:
                raise ctypes.WinError(ctypes.get_last_error())
            raw = premultiplied_bgra(image)
            ctypes.memmove(self.bits, raw, len(raw))
        except BaseException:
            self._release_surface()
            raise
        finally:
            user32.ReleaseDC(None, screen_dc)

    def _position(self) -> tuple[int, int]:
        pet_x, pet_y, pet_width, _ = self.anchor
        x = pet_x + (pet_width - self.width) // 2
        y = pet_y - self.height + 31
        work = monitor_work_area(self.anchor)
        x = max(work.left + 8, min(x, work.right - self.width - 8))
        y = max(work.top + 8, min(y, work.bottom - self.height - 8))
        return x, y

    def show(self, notice: BubbleNotice, anchor: tuple[int, int, int, int]) -> None:
        self._ensure_window()
        image, self.action_rects, self.close_rect = render_bubble(notice)
        self._load_surface(image)
        self.notice = notice
        self.expires_at = time.monotonic() + notice.duration if notice.duration is not None else None
        self.anchor = anchor
        x, y = self._position()
        screen_dc = user32.GetDC(None)
        destination = wintypes.POINT(x, y)
        source = wintypes.POINT(0, 0)
        size = SIZE(self.width, self.height)
        blend = BLENDFUNCTION(0, 0, 255, 1)
        try:
            if not user32.UpdateLayeredWindow(
                self.hwnd, screen_dc, ctypes.byref(destination), ctypes.byref(size),
                self.memory_dc, ctypes.byref(source), 0, ctypes.byref(blend), ULW_ALPHA
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            user32.ReleaseDC(None, screen_dc)
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(
            self.hwnd, ctypes.c_void_p(-1), x, y, self.width, self.height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def ensure_display(self, anchor: tuple[int, int, int, int]) -> bool:
        if not self.hwnd or not user32.IsWindow(self.hwnd):
            return False
        self.anchor = anchor
        x, y = self._position()
        if not user32.SetWindowPos(
            self.hwnd, ctypes.c_void_p(-1), x, y, self.width, self.height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        ):
            return False
        rect = wintypes.RECT()
        return bool(user32.IsWindowVisible(self.hwnd)
                    and user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
                    and (rect.left, rect.top, rect.right, rect.bottom)
                    == (x, y, x + self.width, y + self.height))

    def reposition(self, anchor: tuple[int, int, int, int]) -> None:
        self.anchor = anchor
        if self.hwnd and self.notice:
            x, y = self._position()
            user32.SetWindowPos(
                self.hwnd, ctypes.c_void_p(-1), x, y, 0, 0,
                SWP_NOSIZE | SWP_NOACTIVATE,
            )

    def hide(self) -> None:
        self.notice = None
        self.expires_at = None
        if self.hwnd:
            user32.ShowWindow(self.hwnd, 0)

    def tick(self, now: float) -> None:
        if self.expires_at is not None and now >= self.expires_at:
            self.hide()

    def close(self) -> None:
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
        self._release_surface()

    def _wnd_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == WM_LBUTTONUP:
            x = ctypes.c_short(lparam & 0xFFFF).value
            y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            left, top, right, bottom = self.close_rect
            if left <= x <= right and top <= y <= bottom:
                notice = self.notice
                self.hide()
                if notice:
                    self.on_close(notice)
                return 0
            for index, (left, top, right, bottom) in enumerate(self.action_rects):
                if left <= x <= right and top <= y <= bottom:
                    notice = self.notice
                    if notice:
                        self.on_action(notice, index)
                    return 0
            if self.notice and self.notice.kind == "chat":
                self.hide()
            return 0
        if message == WM_RBUTTONUP:
            notice = self.notice
            self.hide()
            if notice:
                self.on_close(notice)
            return 0
        if message == WM_DESTROY:
            self.notice = None
            self.hwnd = None
            self._release_surface()
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

DAILY_LINES = (
    "今天也要记得喝水呀。",
    "忙了一阵的话，伸个懒腰吧！",
    "我在这里陪着你，加油～",
    "一步一步来，也很了不起。",
    "要不要点点我，换个心情？",
    "辛苦啦，休息一下也没关系。",
)
STATE_LINES = {
    "curious": "今天想一起做点什么？",
    "happy": "看到你啦，嘿嘿！",
    "worried": "别着急，我们慢慢想办法。",
    "sleepy": "唔……要一起休息一会儿吗？",
    "wink": "嘿，给你一个小小的惊喜！",
    "thinking": "让我想想，好主意会来的。",
    "pout": "哼，也要记得照顾自己哦。",
    "excited": "加油！这次也一定能做到！",
}
REMINDER_LINES = {
    "sedentary": ("坐久啦", "站起来走两步吧，肩膀也放松一下。"),
    "water": ("该喝水了", "先喝几口水，我在这里等你回来。"),
    "eye": ("眼睛歇一会儿", "抬头看看远处，二十秒就好。"),
}
FOCUS_DONE_LINES = ("专注完成啦", "这一轮做得很棒，休息几分钟吧。")
BREAK_DONE_LINES = ("休息结束", "准备好了的话，我们再开始下一轮。")

class PetWindow:
    def __init__(self, width: int | None = None, demo_seconds: int = 0):
        try:
            self.controls: ControlStore | None = ControlStore()
            preferences = self.controls.settings()
        except (OSError, sqlite3.Error) as error:
            self.controls = None
            preferences = {**DEFAULTS, "revision": 0}
            log_notice_event("control_store_unavailable", repr(error))
        self.settings_revision = preferences["revision"]
        self.next_settings_poll = 0.0
        try:
            self.sprite_directory = (self.controls.skin_directory(preferences["skin"]) if self.controls else None) or resource_dir()
        except ValueError:
            preferences = self.controls.update_settings({"skin": "default"})
            self.settings_revision = preferences["revision"]
            self.sprite_directory = resource_dir()
        self.width = width or preferences["width"]
        self.height = self.width * 3 // 2
        self.sprites = SpriteSet(self.width, self.height, self.sprite_directory)
        self.bubble = BubbleOverlay(self._bubble_action, self._bubble_close)
        try:
            self.notifications: NotificationStore | None = NotificationStore()
            self.notifications.prune()
            log_notice_event("queue_ready", str(self.notifications.path))
        except (OSError, sqlite3.Error) as error:
            self.notifications = None
            log_notice_event("queue_start_failed", repr(error))
        self.active_notice_id: str | None = None
        self.legacy_bridge = (LegacyQueueBridge(self.notifications, legacy_database_paths())
                              if self.notifications and not os.environ.get("NIJIKA_PET_DB_PATH") else None)
        self.next_legacy_sync = 0.0
        self.last_notice_error_at = 0.0
        self.last_notice_show_log_at = 0.0
        self.next_notice_poll = 0.0
        self.next_health_write = 0.0
        self.last_logged_notice_id: str | None = None
        self.defer_next_notice_until = 0.0
        self.chat_enabled = preferences["chat_enabled"]
        self.next_chat = time.monotonic() + random.uniform(7.0, 11.0)

        try:
            self.companion: CompanionStore | None = CompanionStore()
            self.companion.prune_notes()
            greeting = self.companion.affection()
            log_notice_event("companion_ready", f"days={greeting['days']} stage={greeting['stage']['name']}")
        except (OSError, sqlite3.Error) as error:
            self.companion = None
            log_notice_event("companion_start_failed", repr(error))
        self.next_companion_poll = 0.0
        self.last_reminder_at = 0.0
        self.badge_cache: tuple[str, str] | None = None
        self.state = preferences["expression"]
        self.motion_mode = preferences["motion"]
        self.motion_started = time.monotonic()
        self.blink_until = 0.0
        self.wink_until = 0.0
        self.bounce_started = 0.0
        self.bounce_count = 0
        self.drag_direction = 0
        self.drag_tilt = 0.0
        self.last_tick = time.monotonic()
        self.current_frame: tuple | None = None
        self.drag_start: tuple[int, int, int, int] | None = None
        self.dragged = False
        self.next_blink = time.monotonic() + random.uniform(3.0, 6.0)
        self.next_wink = time.monotonic() + random.uniform(9.0, 15.0)
        self.next_idle_hop = time.monotonic() + random.uniform(12.0, 19.0)
        self.demo_seconds = demo_seconds
        self.high_res_timer = False
        self.hwnd: int | None = None
        self._callback = WNDPROC(self._wnd_proc)
        self.x, self.y = self._initial_position()

    def _initial_position(self) -> tuple[int, int]:
        work = wintypes.RECT()
        if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work), 0):
            return work.right - self.width - 36, work.bottom - self.height - 8
        return 700, 200

    def _cursor(self) -> tuple[int, int]:
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def _bubble_anchor(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    def say(self, phrase: str | None = None) -> None:
        if not self.hwnd:
            return
        if self.bubble.notice and self.bubble.notice.kind in ("agent", "approval"):
            return
        self.bubble.show(
            BubbleNotice("虹夏 · 日常", phrase or random.choice(DAILY_LINES)),
            self._bubble_anchor(),
        )

    def show_demo_notice(self, request_choice: bool = False) -> None:
        if request_choice:
            notice = BubbleNotice(
                "演示选择 · DeepSeek",
                "希望后续提醒怎样展示？",
                actions=("简洁气泡", "详细卡片"),
                action_descriptions=(
                    "只显示关键结论，尽量不打断当前工作。",
                    "同时展示背景与可选步骤，便于判断。",
                ),
                kind="agent", duration=None,
            )
        else:
            notice = BubbleNotice(
                "演示提醒 · Codex",
                "任务已完成，等待你查看结果。",
                actions=("已查看", "稍后"),
                kind="agent", duration=None,
            )
        self.bubble.show(notice, self._bubble_anchor())

    def _poll_notifications(self, now: float) -> None:
        if now < self.next_notice_poll:
            return
        self.next_notice_poll = now + 0.35
        if self.notifications is None:
            try:
                self.notifications = NotificationStore()
                if not os.environ.get("NIJIKA_PET_DB_PATH"):
                    self.legacy_bridge = LegacyQueueBridge(self.notifications, legacy_database_paths())
                log_notice_event("queue_recovered", str(self.notifications.path))
            except (OSError, sqlite3.Error) as error:
                self.next_notice_poll = now + 2.0
                if now - self.last_notice_error_at > 30:
                    log_notice_event("queue_retry_failed", repr(error))
                    self.last_notice_error_at = now
                return
        if now < self.defer_next_notice_until:
            return
        bridge = getattr(self, "legacy_bridge", None)
        if bridge and now >= self.next_legacy_sync:
            self.next_legacy_sync = now + 1.0
            errors = bridge.sync()
            if errors and now - self.last_notice_error_at > 30:
                log_notice_event("legacy_sync_failed", "; ".join(errors))
                self.last_notice_error_at = now
        try:
            pending = self.notifications.next_pending()
        except sqlite3.Error as error:
            if now - self.last_notice_error_at > 30:
                log_notice_event("queue_read_failed", repr(error))
                self.last_notice_error_at = now
            return
        if pending is None:
            if self.bubble.notice and self.bubble.notice.request_id:
                self.bubble.hide()
            self.active_notice_id = None
            return
        if (self.bubble.notice and self.bubble.notice.request_id == pending.id
                and self.bubble.ensure_display(self._bubble_anchor())):
            return
        self.active_notice_id = pending.id
        try:
            self.bubble.show(
                BubbleNotice(f"{pending.agent} · {pending.title}", pending.message,
                             actions=pending.choices,
                             action_descriptions=pending.choice_descriptions,
                             action_recommended=pending.choice_recommended,
                             kind=pending.kind, duration=None,
                             request_id=pending.id),
                self._bubble_anchor(),
            )
        except Exception as error:
            if now - self.last_notice_error_at > 30:
                log_notice_event("bubble_show_failed", repr(error))
                self.last_notice_error_at = now
            return
        if pending.id != self.last_logged_notice_id or now - self.last_notice_show_log_at > 30:
            log_notice_event("bubble_shown",
                             f"id={pending.id} visible={bool(user32.IsWindowVisible(self.bubble.hwnd))}")
            self.last_notice_show_log_at = now
            self.last_logged_notice_id = pending.id
        self.set_state("curious")

    def poll_notifications_safely(self) -> None:
        now = time.monotonic()
        try:
            self._apply_control_settings(now)
        except Exception as error:
            if now - self.last_notice_error_at > 30:
                log_notice_event("control_settings_failed", repr(error))
                self.last_notice_error_at = now
        try:
            self._poll_notifications(now)
        except Exception as error:
            if now - self.last_notice_error_at > 30:
                log_notice_event("notice_poll_failed", repr(error))
                self.last_notice_error_at = now
        finally:
            self._write_notification_health(now)

    def _apply_control_settings(self, now: float) -> None:
        if self.controls is None:
            return
        if now < self.next_settings_poll:
            return
        self.next_settings_poll = now + 1.0
        preferences = self.controls.settings()
        if preferences["revision"] == self.settings_revision:
            return
        try:
            directory = self.controls.skin_directory(preferences["skin"]) or resource_dir()
        except ValueError:
            preferences = self.controls.update_settings({"skin": "default"})
            directory = resource_dir()
        self.resize(preferences["width"], directory=directory)
        if self.motion_mode != preferences["motion"]:
            self.set_motion(preferences["motion"])
        self.set_state(preferences["expression"], react=False)
        self.chat_enabled = preferences["chat_enabled"]
        if not self.chat_enabled and self.bubble.notice and self.bubble.notice.kind == "chat":
            self.bubble.hide()
        self.settings_revision = preferences["revision"]
        self.next_health_write = 0.0

    def _poll_companion(self, now: float) -> None:
        """Turn timer phases and break reminders into one bubble at a time."""
        if self.companion is None or now < self.next_companion_poll:
            return
        self.next_companion_poll = now + 1.0
        try:
            event = self.companion.take_event()
            timer = self.companion.pomodoro()
        except (OSError, sqlite3.Error) as error:
            self.companion = None
            log_notice_event("companion_poll_failed", repr(error))
            return
        self.badge_cache = self._focus_badge(timer)
        busy = self.bubble.notice is not None or self.active_notice_id is not None
        if event and not busy:
            title, text = FOCUS_DONE_LINES if event == "focus_done" else BREAK_DONE_LINES
            self.bubble.show(BubbleNotice(f"虹夏 · {title}", text, duration=9.0), self._bubble_anchor())
            self.set_state("excited" if event == "focus_done" else "happy")
            return
        if timer["status"] == "running" or busy:
            return
        try:
            kind = self.companion.due_reminder()
        except (OSError, sqlite3.Error) as error:
            self.companion = None
            log_notice_event("companion_poll_failed", repr(error))
            return
        if kind:
            title, text = REMINDER_LINES[kind]
            self.bubble.show(BubbleNotice(f"虹夏 · {title}", text, duration=9.0), self._bubble_anchor())
            self.set_state("worried")

    @staticmethod
    def _focus_badge(timer: dict) -> tuple[str, str] | None:
        if timer["status"] not in ("running", "paused"):
            return None
        label = format_countdown(timer["remaining_seconds"])
        return (("暂停 " if timer["status"] == "paused" else "") + label, timer["mode"])

    def record_affection(self, kind: str) -> None:
        if self.companion is None:
            return
        try:
            self.companion.record_interaction(kind)
        except (OSError, sqlite3.Error) as error:
            log_notice_event("affection_save_failed", repr(error))

    def _timer_menu(self) -> tuple[str, str]:
        """Describe the next sensible action for the right-click menu."""
        if self.companion is None:
            return ("start", "专注计时：不可用")
        try:
            timer = self.companion.pomodoro()
        except (OSError, sqlite3.Error):
            return ("start", "专注计时：不可用")
        if timer["status"] == "running":
            return ("pause", "暂停专注 · " + format_countdown(timer["remaining_seconds"]))
        if timer["status"] == "paused":
            return ("resume", "继续专注 · " + format_countdown(timer["remaining_seconds"]))
        return ("start", "开始专注 · " + str(timer["focus_minutes"]) + " 分钟")

    def toggle_focus(self) -> None:
        if self.companion is None:
            self.say("专注计时还没准备好，稍后再试试。")
            return
        try:
            timer = self.companion.pomodoro()
            action = "pause" if timer["status"] == "running" else "resume" if timer["status"] == "paused" else "start"
            result = self.companion.pomodoro_action(action)
        except (OSError, sqlite3.Error, ValueError) as error:
            log_notice_event("focus_action_failed", repr(error))
            self.say("专注计时没能启动，稍后再试试。")
            return
        self.badge_cache = self._focus_badge(result)
        if action == "start":
            self.bubble.show(
                BubbleNotice("虹夏 · 开始专注", f"这一轮 {result['focus_minutes']} 分钟，我陪着你。", duration=5.0),
                self._bubble_anchor(),
            )
            self.start_bounce(1)
        elif action == "pause":
            self.say("好，先休息一下。")
        else:
            self.say("继续加油，我们接着来！")

    def reset_focus(self) -> None:
        if self.companion is None:
            return
        try:
            result = self.companion.pomodoro_action("reset")
        except (OSError, sqlite3.Error, ValueError) as error:
            log_notice_event("focus_reset_failed", repr(error))
            return
        self.badge_cache = self._focus_badge(result)
        self.say("这一轮先到这里，辛苦了。")

    def _write_notification_health(self, now: float) -> None:
        if now < self.next_health_write or self.notifications is None:
            return
        self.next_health_write = now + 3.0
        try:
            path = self.notifications.path
            stat = path.stat()
            rect = wintypes.RECT()
            hwnd = self.bubble.hwnd
            has_rect = hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect))
            payload = {
                "pid": os.getpid(), "heartbeat_at": time.time(),
                "supports_control": self.controls is not None, "applied_revision": self.settings_revision,
                "width": self.width, "motion": self.motion_mode,
                "database": str(path.resolve()), "database_file_id": stat.st_ino,
                "active_notice_id": self.bubble.notice.request_id if self.bubble.notice else None,
                "window_visible": bool(hwnd and user32.IsWindowVisible(hwnd)),
                "bubble_rect": [rect.left, rect.top, rect.right, rect.bottom] if has_rect else None,
            }
            target = path.with_name("renderer-status.json")
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temporary.replace(target)
        except OSError:
            pass

    def _bubble_close(self, notice: BubbleNotice) -> None:
        if not notice.request_id or self.notifications is None:
            return
        try:
            self.notifications.dismiss(notice.request_id)
        except sqlite3.Error:
            pass
        self.active_notice_id = None
        self.next_notice_poll = 0.0

    def _bubble_action(self, notice: BubbleNotice, index: int) -> None:
        if notice.kind not in ("agent", "approval") or index >= len(notice.actions):
            return
        selected = notice.actions[index]
        if notice.request_id:
            if self.notifications is None:
                return
            try:
                result = self.notifications.answer(notice.request_id, index)
            except sqlite3.Error:
                return
            if result is None or result.status != "answered":
                return
            self.active_notice_id = None
            self.defer_next_notice_until = time.monotonic() + 2.5
            self.bubble.show(
                BubbleNotice("虹夏 · 已回复",
                             "已收到审批提醒，请在 Codex 审批卡授权。" if notice.kind == "approval"
                             else f"已选择「{selected}」，Agent 会按此继续。" if any(notice.action_descriptions)
                             else "已收到完成提醒。",
                             duration=2.5),
                self._bubble_anchor(),
            )
            self.set_state("happy")
            return
        self.bubble.show(
            BubbleNotice(
                "虹夏 · 演示结果",
                f"你选择了「{selected}」。这只是本地演示，尚未发送给 Agent。",
                duration=7.0,
            ),
            self._bubble_anchor(),
        )
        self.set_state("happy")

    def show_pose(self, name: str, *, badge: tuple[str, str] | None = None, **pose: float) -> None:
        if not self.hwnd:
            return
        key = (name, *pose.values(), badge)
        if key == self.current_frame:
            return
        self.sprites.render(name, badge=badge, **pose)
        screen_dc = user32.GetDC(None)
        destination = wintypes.POINT(self.x, self.y)
        source = wintypes.POINT(0, 0)
        size = SIZE(self.width, self.height)
        blend = BLENDFUNCTION(0, 0, 255, 1)
        try:
            if not user32.UpdateLayeredWindow(
                self.hwnd, screen_dc, ctypes.byref(destination), ctypes.byref(size),
                self.sprites.memory_dc, ctypes.byref(source), 0,
                ctypes.byref(blend), ULW_ALPHA
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            self.current_frame = key
        finally:
            user32.ReleaseDC(None, screen_dc)

    def start_bounce(self, count: int = 1) -> None:
        if self.motion_mode != "off":
            self.bounce_started = time.monotonic()
            self.bounce_count = count
        self.tick()

    def set_state(self, name: str, *, react: bool = True, bounce_count: int = 1) -> None:
        if name not in EXPRESSIONS:
            return
        self.state = name
        self.blink_until = 0.0
        self.wink_until = 0.0
        user32.SetWindowTextW(self.hwnd, f"虹夏桌宠 · {LABELS[name]}")
        self.next_blink = time.monotonic() + random.uniform(3.0, 6.0)
        self.next_wink = time.monotonic() + random.uniform(9.0, 15.0)
        self.next_idle_hop = time.monotonic() + random.uniform(12.0, 19.0)
        if react:
            self.start_bounce(bounce_count)
        else:
            self.tick()

    def set_motion(self, mode: str) -> None:
        if mode not in ("lively", "gentle", "off"):
            return
        self.motion_mode = mode
        self.motion_started = time.monotonic()
        self.bounce_started = self.blink_until = self.wink_until = 0.0
        self.drag_tilt = 0.0
        self.next_idle_hop = time.monotonic() + random.uniform(12.0, 19.0)
        self.tick()

    def tick(self) -> None:
        now = time.monotonic()
        dt = min(0.10, max(0.0, now - self.last_tick))
        self.last_tick = now
        self.bubble.tick(now)
        if self.chat_enabled and now >= self.next_chat:
            self.next_chat = now + random.uniform(110.0, 180.0)
            if not self.drag_start and self.bubble.notice is None:
                self.say()
        if self.motion_mode == "off":
            self.show_pose(self.state)
            return
        if (
            self.motion_mode == "lively" and self.state != "sleepy"
            and now >= self.next_idle_hop
        ):
            self.bounce_started = now
            self.bounce_count = 1
            self.next_idle_hop = now + random.uniform(12.0, 19.0)
        name = self.state
        if self.state == "curious" and now >= self.next_blink:
            self.blink_until = now + 0.14
            self.next_blink = now + random.uniform(3.0, 6.0)
        if self.motion_mode == "lively" and self.state == "curious" and now >= self.next_wink:
            self.wink_until = now + 0.55
            self.next_wink = now + random.uniform(9.0, 15.0)
        if self.blink_until > now:
            name = "blink"
        elif self.wink_until > now:
            name = "wink"

        elapsed = now - self.motion_started
        strength = 1.0 if self.motion_mode == "lively" else 0.42
        breath = math.sin(elapsed * 2.0 * math.pi / 1.55)
        sway = math.sin(elapsed * 2.0 * math.pi / 2.65)
        shift_y = -1.5 * strength * (breath + 1.0) / 2.0
        scale_x = 1.0 + 0.004 * strength * breath
        scale_y = 1.0 + 0.006 * strength * breath
        angle = 1.25 * strength * sway
        sparkle = 0.0

        dragging = bool(self.drag_start and self.dragged)
        target_tilt = -3.4 * self.drag_direction if dragging else 0.0
        self.drag_tilt += (target_tilt - self.drag_tilt) * (1.0 - math.exp(-12.0 * dt))
        angle += self.drag_tilt

        if self.bounce_started and not dragging:
            duration = 0.62 if self.motion_mode == "lively" else 0.72
            progress = (now - self.bounce_started) / duration
            if progress >= self.bounce_count:
                self.bounce_started = 0.0
            else:
                phase = progress % 1.0
                envelope = max(0.0, math.sin(math.pi * phase))
                lift = envelope ** 1.35
                amount = 1.0 if self.motion_mode == "lively" else 0.45
                shift_y -= 19.0 * amount * lift
                scale_x += 0.025 * amount * math.sin(2.0 * math.pi * phase) ** 2
                scale_y += 0.020 * amount * lift - 0.022 * amount * math.sin(2.0 * math.pi * phase) ** 2
                angle += 1.3 * amount * math.sin(2.0 * math.pi * phase)
                sparkle = max(0.0, min(1.0, (lift - 0.35) * 2.0)) * amount

        self.show_pose(
            name, shift_y=shift_y, angle=angle,
            scale_x=scale_x, scale_y=scale_y, sparkle=sparkle,
            badge=self.badge_cache,
        )

    def resize(self, width: int, *, directory: Path | None = None) -> None:
        directory = directory or self.sprite_directory
        if width == self.width and directory == self.sprite_directory:
            return
        height = width * 3 // 2
        replacement = SpriteSet(width, height, directory)
        previous = self.sprites
        self.x += self.width - width
        self.y += self.height - height
        self.width, self.height, self.sprites = width, height, replacement
        self.sprite_directory = directory
        self.current_frame = None
        user32.SetWindowPos(
            self.hwnd, None, self.x, self.y, width, height,
            SWP_NOZORDER | SWP_NOACTIVATE
        )
        self.bubble.reposition(self._bubble_anchor())
        self.tick()
        previous.close()

    def popup_menu(self) -> None:
        menu = user32.CreatePopupMenu()
        try:
            options = [(101 + index, LABELS[name]) for index, name in enumerate(EXPRESSIONS)]
            timer_action, timer_title = self._timer_menu()
            options += [
                (601, "设置中心 / 添加 Agent"),
                (201, "小号"), (202, "中号"), (203, "大号"),
                (401, "动态：活泼明显"), (402, "动态：轻柔自然"), (403, "动态：关闭"),
                (701, timer_title),
                (702, "结束这一轮专注"),
                (501, "让虹夏说句话"), (502, "演示：完成提醒"),
                (503, "演示：请求选择"),
                (504, "日常闲聊：开启" if self.chat_enabled else "日常闲聊：关闭"),
                (301, "退出桌宠"),
            ]
            for command, title in options:
                if command in (201, 401, 501, 301):
                    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
                checked = (
                    (command == 401 and self.motion_mode == "lively")
                    or (command == 402 and self.motion_mode == "gentle")
                    or (command == 403 and self.motion_mode == "off")
                    or (command == 504 and self.chat_enabled)
                )
                user32.AppendMenuW(menu, MF_STRING | (MF_CHECKED if checked else 0), command, title)
            x, y = self._cursor()
            user32.SetForegroundWindow(self.hwnd)
            command = user32.TrackPopupMenu(
                menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, x, y, 0, self.hwnd, None
            )
        finally:
            user32.DestroyMenu(menu)
        if 101 <= command < 101 + len(EXPRESSIONS):
            self.set_state(EXPRESSIONS[command - 101])
            self.save_control_preferences({"expression": self.state})
        elif 201 <= command <= 203:
            self.resize(WIDTHS[command - 201])
            self.save_control_preferences({"width": self.width})
        elif 401 <= command <= 403:
            self.set_motion(("lively", "gentle", "off")[command - 401])
            self.save_control_preferences({"motion": self.motion_mode})
        elif command == 701:
            self.toggle_focus()
        elif command == 702:
            self.reset_focus()
        elif command == 501:
            self.say()
        elif command == 502:
            self.show_demo_notice()
        elif command == 503:
            self.show_demo_notice(request_choice=True)
        elif command == 504:
            self.chat_enabled = not self.chat_enabled
            self.save_control_preferences({"chat_enabled": self.chat_enabled})
            self.next_chat = time.monotonic() + random.uniform(110.0, 180.0)
            if not self.chat_enabled and self.bubble.notice and self.bubble.notice.kind == "chat":
                self.bubble.hide()
        elif command == 601:
            self.open_control_panel()
        elif command == 301:
            user32.DestroyWindow(self.hwnd)

    def open_control_panel(self) -> None:
        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = wintypes.HWND
        window = user32.FindWindowW(None, "虹夏桌宠 · 设置中心")
        if window:
            user32.ShowWindow(window, 9)
            user32.SetForegroundWindow(window)
            return
        if getattr(sys, "frozen", False):
            command = [str(Path(sys.executable)), "--control-panel"]
        else:
            command = [sys.executable, str(Path(__file__).resolve()), "--control-panel"]
        try:
            subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as error:
            log_notice_event("control_panel_start_failed", repr(error))
            self.say("控制中心未能启动，请检查是否已安装完整程序。")

    def save_control_preferences(self, patch: dict) -> None:
        if self.controls is None:
            return
        try:
            self.controls.update_settings(patch)
        except (OSError, sqlite3.Error) as error:
            log_notice_event("control_settings_save_failed", repr(error))

    def _wnd_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == WM_LBUTTONDOWN:
            x, y = self._cursor()
            self.drag_start = (x, y, self.x, self.y)
            self.dragged = False
            user32.SetCapture(hwnd)
            return 0
        if message == WM_LBUTTONDBLCLK:
            user32.ReleaseCapture()
            self.drag_start = None
            self.dragged = False
            self.set_state("excited", bounce_count=2)
            self.say(STATE_LINES["excited"])
            return 0
        if message == WM_MOUSEMOVE and self.drag_start and wparam & MK_LBUTTON:
            x, y = self._cursor()
            sx, sy, wx, wy = self.drag_start
            dx, dy = x - sx, y - sy
            if abs(dx) > 4 or abs(dy) > 4:
                self.dragged = True
            if self.dragged:
                self.x, self.y = wx + dx, wy + dy
                self.drag_direction = 1 if dx > 3 else -1 if dx < -3 else 0
                user32.SetWindowPos(
                    hwnd, None, self.x, self.y, 0, 0,
                    SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                )
                self.bubble.reposition(self._bubble_anchor())
            return 0
        if message == WM_LBUTTONUP:
            if self.drag_start:
                user32.ReleaseCapture()
                if self.dragged:
                    self.drag_direction = 0
                else:
                    index = (EXPRESSIONS.index(self.state) + 1) % len(EXPRESSIONS)
                    self.set_state(EXPRESSIONS[index])
                    self.say(STATE_LINES[self.state])
                    self.record_affection("pet")
            self.drag_start = None
            self.dragged = False
            self.tick()
            return 0
        if message == WM_RBUTTONUP:
            self.popup_menu()
            return 0
        if message == WM_TIMER:
            try:
                if wparam == 1:
                    self.tick()
                elif wparam == 2:
                    self.poll_notifications_safely()
                    self._poll_companion(time.monotonic())
                elif wparam == 3:
                    user32.DestroyWindow(hwnd)
            except Exception as error:
                if time.monotonic() - self.last_notice_error_at > 30:
                    log_notice_event("timer_failed", repr(error))
                    self.last_notice_error_at = time.monotonic()
            return 0
        if message == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if message == WM_DESTROY:
            user32.KillTimer(hwnd, 1)
            user32.KillTimer(hwnd, 2)
            user32.KillTimer(hwnd, 3)
            if self.high_res_timer:
                winmm.timeEndPeriod(1)
                self.high_res_timer = False
            self.bubble.close()
            self.sprites.close()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def run(self) -> None:
        module = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSW()
        window_class.style = CS_DBLCLKS
        window_class.lpfnWndProc = self._callback
        window_class.hInstance = module
        window_class.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))
        window_class.lpszClassName = WINDOW_CLASS
        if not user32.RegisterClassW(ctypes.byref(window_class)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_APPWINDOW,
            WINDOW_CLASS, f"虹夏桌宠 · {LABELS[self.state]}", WS_POPUP,
            self.x, self.y, self.width, self.height,
            None, None, module, None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.show_pose(self.state)
        self.bubble.owner = self.hwnd
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(
            self.hwnd, ctypes.c_void_p(-1), self.x, self.y,
            self.width, self.height, SWP_NOACTIVATE,
        )
        self.high_res_timer = winmm.timeBeginPeriod(1) == 0
        user32.SetTimer(self.hwnd, 1, 10, None)
        if not user32.SetTimer(self.hwnd, 2, 350, None):
            raise ctypes.WinError(ctypes.get_last_error())
        self.poll_notifications_safely()
        if self.demo_seconds:
            user32.SetTimer(self.hwnd, 3, self.demo_seconds * 1000, None)
        message = wintypes.MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result == 0:
                break
            if result == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))


def main() -> None:
    parser = argparse.ArgumentParser(description="虹夏桌宠")
    parser.add_argument("--self-test", action="store_true", help="check bundled sprite assets")
    parser.add_argument("--control-panel", action="store_true",
                        help="run the settings window instead of the desktop companion")
    parser.add_argument("--demo-seconds", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        print(sprite_metrics())
        return
    if args.control_panel:
        from control_panel import run_panel
        run_panel([])
        return
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        if not user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            user32.SetProcessDPIAware()
    except AttributeError:
        user32.SetProcessDPIAware()
    sprite_metrics()
    PetWindow(demo_seconds=max(0, args.demo_seconds)).run()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        user32.MessageBoxW(None, str(error), "虹夏桌宠启动失败", 0x10)
        raise
