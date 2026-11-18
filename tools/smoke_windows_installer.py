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
from pathlib import Path, PurePosixPath

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


def verify_shortcuts(shortcuts: dict[Path, str], pet: Path) -> None:
    from win32com.client import Dispatch

    shell = Dispatch("WScript.Shell")
    for path, arguments in shortcuts.items():
        assert path.is_file(), path
        shortcut = shell.CreateShortcut(str(path))
        assert Path(shortcut.TargetPath).resolve() == pet.resolve(), path
        assert shortcut.Arguments == arguments, path


def verify(setup: Path, work: Path, *, disposable_session: bool = False,
           upgrade_from: Path | None = None) -> dict:
    folders = require_disposable_session(disposable_session)
    setup = setup.resolve(strict=True)
    if upgrade_from:
        upgrade_from = upgrade_from.resolve(strict=True)
        with setup.open("rb") as candidate, upgrade_from.open("rb") as previous:
            if hashlib.file_digest(candidate, "sha256").digest() == hashlib.file_digest(previous, "sha256").digest():
                raise ValueError("An old-to-new upgrade requires two distinct Setup binaries")
    user_data = Path.home() / ".nijika-desktop-pet"
    if user_data.exists():
        raise RuntimeError("Existing Nijika user data detected; refusing installer test")
    desktop = folders["desktop"]
    start_menu = folders["start_menu"]
    startup = folders["startup"]
    for directory in (desktop, start_menu, startup):
        directory.mkdir(parents=True, exist_ok=True)
    install = work / "收件人 AppData/Nijika Desktop Pet/app"
    hook = install / "dist/虹夏审批提醒.exe"
    common = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
              "/TASKS=desktopicon,autostart", f"/DIR={install}"]
    # Use real shell folders only inside a disposable Windows session. Never
    # redirect the user's known folders through registry edits.
    previous_hook = None
    if upgrade_from:
        run([str(upgrade_from), *common, f"/LOG={work / 'install-previous.log'}"])
        assert not (hook.parent / package_release.APPROVAL_RUNTIME_DIRECTORY).exists()
        previous_hook = hashlib.sha256(hook.read_bytes()).hexdigest()
    user_data.mkdir()
    protected = user_data / "installer-smoke-sentinel.txt"
    sentinel = b"test data that an upgrade and uninstall must preserve"
    protected.write_bytes(sentinel)
    run([str(setup), *common, f"/LOG={work / 'install-candidate.log'}"])
    assert protected.read_bytes() == sentinel
    if previous_hook:
        assert hashlib.sha256(hook.read_bytes()).hexdigest() != previous_hook
    expected_hashes = json.loads((install / "SHA256SUMS.json").read_text(encoding="utf-8"))
    runtime_roots = (package_release.MCP_DIRECTORY, f"dist/{package_release.PET_RUNTIME_DIRECTORY}",
                     f"dist/{package_release.APPROVAL_RUNTIME_DIRECTORY}")
    fixed_files = set(package_release.FILES) - set(runtime_roots)
    optional_files = {"distribution/support.json", "distribution/support.png"}
    assert fixed_files <= expected_hashes.keys()
    for root in runtime_roots:
        assert any(name.startswith(root + "/") for name in expected_hashes), root
    for name, digest in expected_hashes.items():
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts and not {"\\", ":"}.intersection(name), name
        assert name in fixed_files | optional_files or name.startswith(tuple(root + "/" for root in runtime_roots)), name
        if name != "plugins/nijika-work-local/mcp.json":
            assert hashlib.sha256((install / name).read_bytes()).hexdigest() == digest, name
    assert (install / package_release.MCP_EXECUTABLE).is_file()
    for root in runtime_roots[1:]:
        for filename in ("base_library.zip", "python312.dll"):
            assert f"{root}/{filename}" in expected_hashes
    manifest = json.loads((install / "plugins/nijika-work-local/mcp.json").read_text(encoding="utf-8"))
    executable = manifest["mcpServers"]["nijika-work-pet"]["args"][-1]
    assert Path(executable) == install / "dist/虹夏MCP-v2/虹夏MCP-v2.exe", executable
    assert "AUTO_LOCAL_MCP" not in executable
    source_digests = {
        name: digest for name, digest in expected_hashes.items()
        if name != "plugins/nijika-work-local/mcp.json"
    }
    uninstallers = list(install.glob("unins*.exe"))
    assert len(uninstallers) == 1
    uninstaller = uninstallers[0]
    assert (install / "unins000.dat").is_file()
    shortcuts = {
        desktop / "虹夏桌宠.lnk": "",
        desktop / "虹夏桌宠设置.lnk": "--control-panel",
        start_menu / "虹夏桌宠/虹夏桌宠.lnk": "",
        start_menu / "虹夏桌宠/虹夏桌宠设置.lnk": "--control-panel",
        startup / "虹夏桌宠.lnk": "",
    }
    verify_shortcuts(shortcuts, install / "dist/虹夏桌宠.exe")

    # A repeat install must retain both program integrity and user-owned data.
    (install / "dist/nijika-notice.log").write_text("generated diagnostic", encoding="utf-8")
    run([str(setup), *common, f"/LOG={work / 'reinstall.log'}"])
    assert protected.read_bytes() == sentinel
    for name, digest in source_digests.items():
        assert hashlib.sha256((install / name).read_bytes()).hexdigest() == digest, name
    verify_shortcuts(shortcuts, install / "dist/虹夏桌宠.exe")

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
    for name in expected_hashes:
        assert not (install / name).exists(), name
    assert protected.read_bytes() == sentinel
    assert not any(path.exists() for path in shortcuts)
    return {
        "status": "passed",
        "custom_chinese_spaced_install_root": True,
        "files": len(expected_hashes) + 1,
        "work_mcp_path_rewritten": True,
        "fresh_install": upgrade_from is None,
        "legacy_onefile_upgrade": upgrade_from is not None,
        "repeat_install": True,
        "default_user_data_sentinel_preserved": True,
        "silent_uninstall": True,
        "shortcut_targets_verified": True,
        "shortcuts_removed": True,
        "disposable_windows_session": True,
        "known_folder_registry_not_modified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=Path)
    parser.add_argument("--upgrade-from", type=Path,
                        help="Install the real legacy Setup first, then upgrade it to the candidate")
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
            disposable_session=args.disposable_windows_session, upgrade_from=args.upgrade_from,
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
