"""Run the native pet and its on-demand WebView2 settings in one process."""

from __future__ import annotations

import ctypes
import hashlib
import os
import signal
import threading
from ctypes import wintypes

from notification_store import default_database_path


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]

ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 258
WM_CLOSE = 0x0010


def run_desktop(create_pet, *, open_settings: bool) -> None:
    database_path = os.path.normcase(str(default_database_path().resolve()))
    identifier = hashlib.sha256(database_path.encode("utf-8")).hexdigest()
    name = f"Local\\NijikaDesktopPet-{identifier}"
    # Create the event first so a shortcut arriving during startup can signal it
    # as soon as the primary process owns the named instance handle.
    event = kernel32.CreateEventW(None, False, False, name + "-settings")
    if not event:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        ctypes.set_last_error(0)
        instance = kernel32.CreateMutexW(None, False, name)
        existing = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        if not instance:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if open_settings:
                kernel32.SetEvent(event)
            if not existing:
                _run_primary(create_pet, event)
        finally:
            kernel32.CloseHandle(instance)
    finally:
        kernel32.CloseHandle(event)


def _wait_for_settings(event: int) -> bool:
    result = kernel32.WaitForSingleObject(event, 200)
    if result in (WAIT_OBJECT_0, WAIT_TIMEOUT):
        return result == WAIT_OBJECT_0
    raise ctypes.WinError(ctypes.get_last_error())


def _run_primary(create_pet, event: int) -> None:
    pet = create_pet(lambda: kernel32.SetEvent(event))
    failures = []

    def run_pet():
        try:
            pet.run()
        except Exception as error:
            failures.append(error)

    pet_thread = threading.Thread(target=run_pet, name="desktop-pet")
    pet_thread.start()
    try:
        while pet_thread.is_alive():
            if _wait_for_settings(event) and pet_thread.is_alive():
                _open_panel(event, pet_thread)
    finally:
        if pet_thread.is_alive() and pet.hwnd:
            user32.PostMessageW(pet.hwnd, WM_CLOSE, 0, 0)
        pet_thread.join()
    if failures:
        raise failures[0]


def _open_panel(event: int, pet_thread: threading.Thread) -> None:
    from control_panel import run_panel

    panel_done = threading.Event()
    watcher = None

    def watch_window(window):
        nonlocal watcher
        watcher = threading.current_thread()
        # pywebview owns its WinForms loop. These window methods marshal to it.
        while not panel_done.is_set() and not window.events.closed.is_set():
            if not window.events.shown.wait(0.2):
                continue
            if not pet_thread.is_alive():
                window.destroy()
                return
            if _wait_for_settings(event):
                if window.events.closed.is_set():
                    kernel32.SetEvent(event)
                    return
                try:
                    if user32.IsIconic(window.native.Handle.ToInt64()):
                        window.restore()
                    window.show()
                except Exception:
                    # A shortcut may arrive while the user closes the window.
                    kernel32.SetEvent(event)
                    return

    previous_sigint = signal.getsignal(signal.SIGINT)
    try:
        run_panel([], watch_window=watch_window)
    except Exception as error:
        user32.MessageBoxW(None, str(error), "虹夏设置中心启动失败", 0x10)
    finally:
        panel_done.set()
        if watcher is not None:
            watcher.join()
        signal.signal(signal.SIGINT, previous_sigint)
