"""Safely remove stale PyInstaller onefile directories from Nijika MCP runs.

The tool is dry-run by default. It only considers direct ``_MEI*`` children of
the selected temporary root that contain the full runtime fingerprint used by
the previous ``虹夏MCP-v2.exe`` onefile build. Directories referenced by any
currently running process are always skipped.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import sys
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path


RUNTIME_FILE_FINGERPRINT = frozenset({
    "python312.dll",
    "base_library.zip",
    "_sqlite3.pyd",
    "_socket.pyd",
    "_wmi.pyd",
})
RUNTIME_DIRECTORY_FINGERPRINT = frozenset({
    "httpx2-2.13.1.dist-info",
    "opentelemetry_api-1.45.1.dist-info",
    "pydantic_core",
})
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_PATH = 260


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    ]


@dataclass(frozen=True)
class Candidate:
    path: str
    bytes: int
    age_hours: float
    active: bool
    eligible: bool
    reason: str


def _windows_temp_roots_from_modules() -> set[Path]:
    """Return active PyInstaller roots observed in loaded process modules."""
    if os.name != "nt":
        return set()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    kernel32.Module32FirstW.restype = wintypes.BOOL
    kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    kernel32.Module32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    roots: set[Path] = set()
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return roots
    try:
        process = PROCESSENTRY32W()
        process.dwSize = ctypes.sizeof(process)
        available = kernel32.Process32FirstW(snapshot, ctypes.byref(process))
        while available:
            module_snapshot = kernel32.CreateToolhelp32Snapshot(
                TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
                process.th32ProcessID,
            )
            if module_snapshot != INVALID_HANDLE_VALUE:
                try:
                    module = MODULEENTRY32W()
                    module.dwSize = ctypes.sizeof(module)
                    present = kernel32.Module32FirstW(module_snapshot, ctypes.byref(module))
                    while present:
                        parts = Path(module.szExePath).parts
                        for index, part in enumerate(parts):
                            if part.casefold().startswith("_mei") and len(part) > 4:
                                roots.add(Path(*parts[:index + 1]))
                                break
                        present = kernel32.Module32NextW(module_snapshot, ctypes.byref(module))
                finally:
                    kernel32.CloseHandle(module_snapshot)
            available = kernel32.Process32NextW(snapshot, ctypes.byref(process))
    finally:
        kernel32.CloseHandle(snapshot)
    return roots


def _directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _runtime_fingerprint(path: Path) -> tuple[set[str], set[str]]:
    try:
        files = {child.name.casefold() for child in path.iterdir()
                 if child.is_file() and not child.is_symlink()}
        directories = {child.name.casefold() for child in path.iterdir()
                       if child.is_dir() and not child.is_symlink()}
        return files, directories
    except OSError:
        return set(), set()


def scan(temp_root: Path, min_age_hours: float = 24.0,
         active_roots: set[Path] | None = None) -> list[Candidate]:
    root = temp_root.resolve(strict=True)
    active = {path.resolve() for path in (active_roots or set())}
    now = time.time()
    result: list[Candidate] = []
    for path in root.iterdir():
        if not path.name.casefold().startswith("_mei") or not path.is_dir():
            continue
        resolved = path.resolve()
        is_reparse = path.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(path)
        try:
            age_hours = max(0.0, (now - path.stat().st_mtime) / 3600)
            size = _directory_size(path) if not is_reparse else 0
        except OSError:
            continue
        in_root = resolved.parent == root
        active_match = any(resolved == value or resolved.is_relative_to(value)
                           for value in active)
        files, directories = _runtime_fingerprint(path)
        fingerprint = (
            files.issuperset(RUNTIME_FILE_FINGERPRINT)
            and directories.issuperset(RUNTIME_DIRECTORY_FINGERPRINT)
        )
        if not in_root:
            reason = "resolved outside temp root"
        elif is_reparse:
            reason = "reparse point"
        elif active_match:
            reason = "active process"
        elif age_hours < min_age_hours:
            reason = "recent"
        elif not fingerprint:
            reason = "runtime fingerprint mismatch"
        else:
            reason = "stale Nijika MCP runtime"
        result.append(Candidate(
            str(path), size, round(age_hours, 2), active_match,
            reason == "stale Nijika MCP runtime", reason,
        ))
    return sorted(result, key=lambda item: item.path.casefold())


def apply(candidates: list[Candidate], temp_root: Path) -> tuple[list[str], list[dict]]:
    root = temp_root.resolve(strict=True)
    deleted: list[str] = []
    failed: list[dict] = []
    for item in candidates:
        if not item.eligible:
            continue
        path = Path(item.path)
        try:
            resolved = path.resolve(strict=True)
            if resolved.parent != root or getattr(os.path, "isjunction", lambda _: False)(path):
                raise OSError("path safety check changed before deletion")
            shutil.rmtree(path)
            deleted.append(str(path))
        except OSError as error:
            failed.append({"path": str(path), "error": str(error)})
    return deleted, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-root", type=Path, default=Path(os.environ.get("TEMP", "")))
    parser.add_argument("--min-age-hours", type=float, default=24.0)
    parser.add_argument("--apply", action="store_true",
                        help="Delete eligible directories; default is a read-only dry run.")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this file.")
    parser.add_argument("--summary-only", action="store_true",
                        help="Omit the per-directory list from console and report output.")
    args = parser.parse_args()
    if args.min_age_hours < 0:
        parser.error("--min-age-hours must be zero or greater")
    if not args.temp_root or not args.temp_root.is_dir():
        parser.error("--temp-root must be an existing directory")
    candidates = scan(args.temp_root, args.min_age_hours, _windows_temp_roots_from_modules())
    deleted, failed = apply(candidates, args.temp_root) if args.apply else ([], [])
    deleted_set = set(deleted)
    report = {
        "mode": "apply" if args.apply else "dry-run",
        "temp_root": str(args.temp_root.resolve()),
        "minimum_age_hours": args.min_age_hours,
        "directories_seen": len(candidates),
        "eligible_directories": sum(item.eligible for item in candidates),
        "eligible_bytes": sum(item.bytes for item in candidates if item.eligible),
        "active_directories": sum(item.active for item in candidates),
        "deleted_directories": len(deleted),
        "reclaimed_bytes": sum(item.bytes for item in candidates
                               if item.path in deleted_set),
        "failed": failed,
    }
    if not args.summary_only:
        report["directories"] = [asdict(item) for item in candidates]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
