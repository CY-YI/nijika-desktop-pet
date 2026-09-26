"""A small, per-pixel-transparent Windows desktop companion."""

from __future__ import annotations

import argparse
import ctypes
import math
import random
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageDraw


EXPRESSIONS = (
    "curious", "happy", "worried", "sleepy", "wink", "thinking", "pout", "excited"
)
SPRITE_NAMES = (*EXPRESSIONS, "blink")
LABELS = {
    "curious": "好奇", "happy": "开心", "worried": "求助", "sleepy": "安睡",
    "wink": "眨眼俏皮", "thinking": "思考", "pout": "小生气", "excited": "加油",
}
WINDOW_CLASS = "NijikaDesktopPetWindow"
WIDTHS = (260, 320, 380)

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
CS_DBLCLKS = 0x0008
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
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
    def __init__(self, width: int, height: int):
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
                with Image.open(resource_dir() / f"{name}.png") as source:
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

    def render(self, name: str, **pose: float) -> None:
        image = render_pose(self.sources[name], **pose)
        raw = premultiplied_bgra(image)
        ctypes.memmove(self.bits, raw, len(raw))


class PetWindow:
    def __init__(self, width: int = 320, demo_seconds: int = 0):
        self.width = width
        self.height = width * 3 // 2
        self.sprites = SpriteSet(self.width, self.height)
        self.state = "curious"
        self.motion_mode = "lively"
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

    def show_pose(self, name: str, **pose: float) -> None:
        if not self.hwnd:
            return
        key = (name, *pose.values())
        if key == self.current_frame:
            return
        self.sprites.render(name, **pose)
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
        )

    def resize(self, width: int) -> None:
        if width == self.width:
            return
        height = width * 3 // 2
        replacement = SpriteSet(width, height)
        previous = self.sprites
        self.x += self.width - width
        self.y += self.height - height
        self.width, self.height, self.sprites = width, height, replacement
        self.current_frame = None
        user32.SetWindowPos(
            self.hwnd, None, self.x, self.y, width, height,
            SWP_NOZORDER | SWP_NOACTIVATE
        )
        self.tick()
        previous.close()

    def popup_menu(self) -> None:
        menu = user32.CreatePopupMenu()
        try:
            options = [(101 + index, LABELS[name]) for index, name in enumerate(EXPRESSIONS)]
            options += [
                (201, "小号"), (202, "中号"), (203, "大号"),
                (401, "动态：活泼明显"), (402, "动态：轻柔自然"), (403, "动态：关闭"),
                (301, "退出桌宠"),
            ]
            for command, title in options:
                if command in (201, 401, 301):
                    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
                checked = (
                    (command == 401 and self.motion_mode == "lively")
                    or (command == 402 and self.motion_mode == "gentle")
                    or (command == 403 and self.motion_mode == "off")
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
        elif 201 <= command <= 203:
            self.resize(WIDTHS[command - 201])
        elif 401 <= command <= 403:
            self.set_motion(("lively", "gentle", "off")[command - 401])
        elif command == 301:
            user32.DestroyWindow(self.hwnd)

    def _wnd_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == WM_LBUTTONDOWN:
            x, y = self._cursor()
            self.drag_start = (x, y, self.x, self.y)
            self.dragged = False
            user32.SetCapture(hwnd)
            return 0
        if message == WM_LBUTTONDBLCLK:
            self.drag_start = None
            self.dragged = False
            self.set_state("excited", bounce_count=2)
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
            return 0
        if message == WM_LBUTTONUP:
            if self.drag_start:
                user32.ReleaseCapture()
                if self.dragged:
                    self.drag_direction = 0
                else:
                    index = (EXPRESSIONS.index(self.state) + 1) % len(EXPRESSIONS)
                    self.set_state(EXPRESSIONS[index])
            self.drag_start = None
            self.dragged = False
            self.tick()
            return 0
        if message == WM_RBUTTONUP:
            self.popup_menu()
            return 0
        if message == WM_TIMER:
            if wparam == 1:
                self.tick()
            elif wparam == 3:
                user32.DestroyWindow(hwnd)
            return 0
        if message == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if message == WM_DESTROY:
            user32.KillTimer(hwnd, 1)
            user32.KillTimer(hwnd, 3)
            if self.high_res_timer:
                winmm.timeEndPeriod(1)
                self.high_res_timer = False
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
            WINDOW_CLASS, "虹夏桌宠 · 好奇", WS_POPUP,
            self.x, self.y, self.width, self.height,
            None, None, module, None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.show_pose(self.state)
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(
            self.hwnd, ctypes.c_void_p(-1), self.x, self.y,
            self.width, self.height, SWP_NOACTIVATE,
        )
        self.high_res_timer = winmm.timeBeginPeriod(1) == 0
        user32.SetTimer(self.hwnd, 1, 10, None)
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
    parser.add_argument("--demo-seconds", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        print(sprite_metrics())
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
