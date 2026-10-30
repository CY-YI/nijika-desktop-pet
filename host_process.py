"""Bounded Windows executable ancestry; no command lines, environment or WMI."""
from __future__ import annotations

import os


def editor_host() -> str:
    if os.name != "nt":
        return ""
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if not handle or handle == ctypes.c_void_p(-1).value:
        return ""
    processes = {}
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        active = kernel.Process32FirstW(handle, ctypes.byref(entry))
        for _ in range(16384):
            if not active:
                break
            processes[entry.th32ProcessID] = (entry.th32ParentProcessID, entry.szExeFile)
            active = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return from_ancestry(processes, os.getpid())


def from_ancestry(processes: dict, pid: int) -> str:
    seen = set()
    for _ in range(16):
        if pid in seen or pid not in processes:
            break
        seen.add(pid)
        parent, name = processes[pid]
        if name.casefold() == "code.exe":
            return "VS Code"
        if name.casefold() == "code - insiders.exe":
            return "VS Code Insiders"
        # An embedded terminal can launch CLI agents too. Do not label those
        # editor extensions just because their distant ancestor is Code.exe.
        if name.casefold() in {"cmd.exe", "powershell.exe", "pwsh.exe", "bash.exe", "wsl.exe"}:
            return ""
        pid = parent
    return ""
