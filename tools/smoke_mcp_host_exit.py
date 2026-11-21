"""Exercise server process exit when an isolated stdio host stops abruptly."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import win32api
import win32con
import win32event
import win32process

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notification_store import NotificationStore  # noqa: E402


def run_host(executable: Path, ready: Path, request_id: str) -> None:
    command = [sys.executable, str(executable)] if executable.suffix == ".py" else [str(executable)]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          creationflags=subprocess.CREATE_NO_WINDOW) as server:
        def send(method, params=None, identifier=None):
            message = {"jsonrpc": "2.0", "method": method}
            if params is not None:
                message["params"] = params
            if identifier is not None:
                message["id"] = identifier
            server.stdin.write(json.dumps(message).encode() + b"\n")
            server.stdin.flush()

        send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                            "clientInfo": {"name": "isolated-exit-smoke", "version": "1"}}, 1)
        reply = json.loads(server.stdout.readline())
        if "result" not in reply or reply.get("id") != 1:
            raise RuntimeError("Candidate MCP initialize failed")
        send("notifications/initialized")
        send("tools/call", {"name": "wait_for_reply", "arguments": {
            "request_id": request_id, "timeout_seconds": 60,
        }}, 2)
        handoff = ready.with_suffix(".tmp")
        handoff.write_text(str(server.pid), encoding="ascii")
        handoff.replace(ready)
        # The test supervisor opens the exact process handle before allowing
        # this host to leave without closing the pipes in application code.
        if sys.stdin.buffer.readline() == b"exit\n":
            os._exit(23)
        server.stdin.close()
        server.wait(timeout=10)


def verify(executable: Path, repetitions: int = 3) -> None:
    executable = executable.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="nijika-host-exit-") as directory:
        isolated = Path(directory)
        temp = isolated / "temp"
        temp.mkdir()
        store = NotificationStore(isolated / "state/notifications.sqlite3")
        env = {**os.environ, "TEMP": str(temp), "TMP": str(temp),
               "NIJIKA_PET_DB_PATH": str(store.path)}
        for index in range(repetitions):
            ready = isolated / f"host-{index}.pid"
            notice = store.create("Test", "Isolated process test", "Waiting for a test reply", ("Acknowledge",))
            command = [sys.executable, __file__, str(executable), "--host-ready", str(ready),
                       "--request-id", notice.id]
            log = isolated / f"host-{index}.log"
            with log.open("wb") as stderr, subprocess.Popen(command, stdin=subprocess.PIPE, env=env, stderr=stderr,
                                  creationflags=subprocess.CREATE_NO_WINDOW) as host:
                try:
                    deadline = time.monotonic() + 15
                    while not ready.is_file():
                        if host.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError("Isolated host did not initialize its MCP connection")
                        time.sleep(0.05)
                    pid = int(ready.read_text(encoding="ascii"))
                    access = (win32con.SYNCHRONIZE | win32con.PROCESS_QUERY_INFORMATION
                              | win32con.PROCESS_TERMINATE)
                    handle = win32api.OpenProcess(access, False, pid)
                    try:
                        assert win32event.WaitForSingleObject(handle, 0) == win32con.WAIT_TIMEOUT
                        time.sleep(0.15)
                        host.communicate(b"exit\n", timeout=5)
                        assert host.returncode == 23
                        result = win32event.WaitForSingleObject(handle, 8000)
                        assert result == win32event.WAIT_OBJECT_0, "MCP survived the closed host pipes"
                        exit_code = win32process.GetExitCodeProcess(handle)
                    finally:
                        # Recover only the test subprocess we opened while its
                        # owning host was alive, even if the test times out.
                        try:
                            if win32event.WaitForSingleObject(handle, 0) == win32con.WAIT_TIMEOUT:
                                win32api.TerminateProcess(handle, 1)
                                win32event.WaitForSingleObject(handle, 5000)
                        finally:
                            handle.Close()
                finally:
                    if host.poll() is None:
                        host.kill()
                        host.wait(timeout=5)
            details = log.read_text(encoding="utf-8", errors="replace")
            assert exit_code == 0, f"MCP exited with code {exit_code}:\n{details}"
            assert "Traceback" not in details and "[PYI-" not in details, details
            assert store.get(notice.id).status == "pending", "Host exit changed the pending notification"
            assert not list(temp.glob("_MEI*")), "Candidate MCP left a temporary extraction directory"
    print(f"MCP exited cleanly after {repetitions}/{repetitions} abrupt host exits with a pending reply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--host-ready", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--request-id", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.host_ready:
        run_host(args.executable, args.host_ready, args.request_id)
    else:
        verify(args.executable)
