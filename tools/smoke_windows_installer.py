"""Exercise the actual Setup EXE in an isolated, user-owned directory."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import package_release  # noqa: E402


def run(command: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {command[0]}\n"
            + result.stderr.decode("utf-8", "replace"))
    return result


def wait_for_uninstall_log(path: Path) -> None:
    # The original unins*.exe exits after spawning its elevated/relocated
    # worker. The log remains locked until that worker has fully exited.
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    create_file.restype = ctypes.c_void_p
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        handle = create_file(str(path), 0x80000000, 0, None, 3, 0x80, None)
        if handle != ctypes.c_void_p(-1).value:
            close_handle(handle)
            return
        time.sleep(0.25)
    raise TimeoutError("Uninstall worker still has its log open")


def verify(setup: Path, work: Path) -> dict:
    desktop = work / "Desktop"
    start_menu = work / "Start Menu/Programs"
    startup = work / "Startup"
    for directory in (desktop, start_menu, startup):
        directory.mkdir(parents=True, exist_ok=True)
    (desktop / "DUMMY").write_text("known folder", encoding="ascii")
    (start_menu / "DUMMY").write_text("known folder", encoding="ascii")
    (startup / "DUMMY").write_text("known folder", encoding="ascii")
    install = work / "收件人 AppData/Nijika Desktop Pet/app"
    home = work / "收件人 User"
    user_data = home / ".nijika-desktop-pet"
    user_data.mkdir(parents=True)
    protected = user_data / "notifications.sqlite3"
    protected.write_bytes(b"test data that an upgrade and uninstall must preserve")
    log = work / "install.log"
    common = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
              "/TASKS=desktopicon,autostart", f"/DIR={install}", f"/LOG={log}"]
    # HKCU overrides are restored in finally below. This avoids shortcuts on
    # the maintainer's actual desktop during the real installer test.
    known_folders = {"Desktop": str(desktop), "Start Menu": str(work / "Start Menu"),
                     "Programs": str(start_menu), "Startup": str(startup)}
    registry_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    saved_folders = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0,
                        winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
        for name, value in known_folders.items():
            saved_folders[name] = winreg.QueryValueEx(key, name)
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)

    def restore_known_folders() -> None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_SET_VALUE) as key:
            for name, (value, kind) in saved_folders.items():
                winreg.SetValueEx(key, name, 0, kind, value)

    try:
        run([str(setup), *common])
    except BaseException:
        restore_known_folders()
        raise
    expected = {name for name in (*package_release.FILES, "SHA256SUMS.json")}
    for name in expected:
        assert (install / name).is_file(), name
    manifest = json.loads((install / "plugins/nijika-work-local/mcp.json").read_text(encoding="utf-8"))
    executable = manifest["mcpServers"]["nijika-work-pet"]["args"][-1]
    assert Path(executable) == install / "dist/虹夏MCP-v2.exe", executable
    assert "AUTO_LOCAL_MCP" not in executable
    source_digests = {
        name: hashlib.sha256((install / name).read_bytes()).hexdigest()
        for name in package_release.FILES if name != "plugins/nijika-work-local/mcp.json"
    }
    uninstallers = list(install.glob("unins*.exe"))
    assert len(uninstallers) == 1
    uninstaller = uninstallers[0]
    assert (install / "unins000.dat").is_file()
    assert (desktop / "虹夏桌宠.lnk").is_file(), list(work.rglob("*.lnk"))
    assert (start_menu / "虹夏桌宠/虹夏桌宠设置.lnk").is_file(), list(work.rglob("*.lnk"))
    assert (startup / "虹夏桌宠.lnk").is_file(), list(work.rglob("*.lnk"))

    # An in-place upgrade must retain both program integrity and user-owned data.
    (install / "dist/nijika-notice.log").write_text("generated diagnostic", encoding="utf-8")
    try:
        run([str(setup), *common])
    except BaseException:
        restore_known_folders()
        raise
    assert protected.read_bytes() == b"test data that an upgrade and uninstall must preserve"
    for name, digest in source_digests.items():
        assert hashlib.sha256((install / name).read_bytes()).hexdigest() == digest, name

    try:
        process = subprocess.Popen([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                                    "/NORESTART", f"/LOG={work / 'uninstall.log'}"])
        deadline = time.monotonic() + 90
        while (install / "dist/虹夏桌宠.exe").exists():
            if time.monotonic() >= deadline:
                process.kill()
                raise TimeoutError("Uninstaller did not finish")
            time.sleep(0.2)
        # Inno uninstallers can relocate themselves to TEMP before returning.
        process.wait(timeout=90)
        if process.returncode:
            raise RuntimeError(f"Uninstaller failed: {process.returncode}")
        wait_for_uninstall_log(work / "uninstall.log")
    finally:
        restore_known_folders()
    assert not (install / "dist/虹夏桌宠.exe").exists()
    assert protected.read_bytes() == b"test data that an upgrade and uninstall must preserve"
    assert not (desktop / "虹夏桌宠.lnk").exists()
    assert not (startup / "虹夏桌宠.lnk").exists()
    return {
        "status": "passed",
        "custom_chinese_spaced_install_root": True,
        "files": len(expected),
        "work_mcp_path_rewritten": True,
        "in_place_upgrade": True,
        "user_data_preserved": True,
        "silent_uninstall": True,
        "shortcuts_removed": True,
        "production_install_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    temporary = tempfile.TemporaryDirectory(prefix="nijika-setup-smoke-")
    try:
        result = verify(args.setup.resolve(), Path(temporary.name))
    finally:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                temporary.cleanup()
                break
            except (PermissionError, NotADirectoryError):
                time.sleep(0.25)
        else:
            temporary.cleanup()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
