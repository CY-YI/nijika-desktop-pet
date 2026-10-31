"""Exercise Setup only in a disposable Windows Sandbox or VM session."""
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


def known_folder(identifier: int) -> Path:
    buffer = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, identifier, None, 0, buffer)
    if result != 0 or not buffer.value:
        raise RuntimeError("Cannot resolve Windows shell folder; refusing installer test")
    path = Path(buffer.value)
    if not path.is_absolute() or "nijika-setup-smoke-" in str(path).lower():
        raise RuntimeError("Invalid Windows shell folder; refusing installer test")
    return path


def require_disposable_session(confirmed: bool) -> dict[str, Path]:
    if not confirmed:
        raise RuntimeError(
            "Installer smoke tests require a disposable Windows Sandbox or VM. "
            "Inside that session only, pass --disposable-windows-session. "
            "This test must not run in your everyday Windows account."
        )
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable; refusing installer test")
    if (Path(local_app_data) / "NijikaDesktopPet").exists():
        raise RuntimeError("Existing Nijika installation detected; refusing installer test")
    uninstall_key = (
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        r"\{D72B6BFA-8D47-46B7-8F5D-CBBF16BB68A0}_is1"
    )
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_key)
    except FileNotFoundError:
        pass
    else:
        key.Close()
        raise RuntimeError("Existing Nijika uninstall registration detected")
    folders = {
        "desktop": known_folder(0x10),
        "start_menu": known_folder(0x02),
        "startup": known_folder(0x07),
    }
    existing = [
        folders["desktop"] / "虹夏桌宠.lnk",
        folders["desktop"] / "虹夏桌宠设置.lnk",
        folders["start_menu"] / "虹夏桌宠",
        folders["startup"] / "虹夏桌宠.lnk",
    ]
    if any(path.exists() for path in existing):
        raise RuntimeError("Existing Nijika shortcuts detected; refusing installer test")
    return folders


def verify(setup: Path, work: Path, *, disposable_session: bool = False) -> dict:
    folders = require_disposable_session(disposable_session)
    desktop = folders["desktop"]
    start_menu = folders["start_menu"]
    startup = folders["startup"]
    for directory in (desktop, start_menu, startup):
        directory.mkdir(parents=True, exist_ok=True)
    install = work / "收件人 AppData/Nijika Desktop Pet/app"
    home = work / "收件人 User"
    user_data = home / ".nijika-desktop-pet"
    user_data.mkdir(parents=True)
    protected = user_data / "notifications.sqlite3"
    protected.write_bytes(b"test data that an upgrade and uninstall must preserve")
    log = work / "install.log"
    common = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
              "/TASKS=desktopicon,autostart", f"/DIR={install}", f"/LOG={log}"]
    # Use real shell folders only inside a disposable Windows session. Never
    # redirect the user's known folders through registry edits.
    run([str(setup), *common])
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
    run([str(setup), *common])
    assert protected.read_bytes() == b"test data that an upgrade and uninstall must preserve"
    for name, digest in source_digests.items():
        assert hashlib.sha256((install / name).read_bytes()).hexdigest() == digest, name

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
        "disposable_windows_session": True,
        "known_folder_registry_not_modified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--disposable-windows-session", action="store_true",
        help="Confirm this runs in a disposable Windows Sandbox/VM, not your daily account",
    )
    args = parser.parse_args()
    require_disposable_session(args.disposable_windows_session)
    temporary = tempfile.TemporaryDirectory(prefix="nijika-setup-smoke-")
    try:
        result = verify(
            args.setup.resolve(), Path(temporary.name),
            disposable_session=args.disposable_windows_session,
        )
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
