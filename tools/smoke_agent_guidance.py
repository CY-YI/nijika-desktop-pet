"""Check the frozen settings/Agent handoff against disposable local data.

This exercises the API, not browser layout or external clients' autonomous calls.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(executable: Path) -> dict:
    executable = executable.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="nijika-guide-smoke-") as temporary:
        isolated = Path(temporary)
        database = isolated / "state/notifications.sqlite3"
        user = isolated / "user"
        shutdown_file = isolated / "shutdown.signal"
        temp = isolated / "temp"
        temp.mkdir()
        environment = {**os.environ, "NIJIKA_PET_DB_PATH": str(database),
                       "TEMP": str(temp), "TMP": str(temp)}
        process = subprocess.Popen(
            [str(executable), "--control-panel", "--serve-only", "--agent-home", str(user),
             "--test-shutdown-file", str(shutdown_file)],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            status = database.parent / "panel-status.json"
            deadline = time.monotonic() + 25
            while not status.is_file():
                if process.poll() is not None:
                    raise RuntimeError("Frozen panel exited before starting its service")
                if time.monotonic() > deadline:
                    raise TimeoutError("Frozen panel did not start within 25 seconds")
                time.sleep(0.1)
            panel = json.loads(status.read_text(encoding="utf-8"))
            origin = panel["url"]
            assert origin.startswith("http://127.0.0.1:")
            with urlopen(origin, timeout=5) as response:
                html = response.read().decode("utf-8")
            token = re.search(r'name="nijika-token" content="([^"]+)"', html).group(1)
            assert token != "NIJIKA_SESSION_TOKEN"

            def call(route, payload=None):
                request = Request(origin + route, json.dumps(payload).encode("utf-8") if payload is not None else None,
                                  {"X-Nijika-Token": token, "Content-Type": "application/json"})
                try:
                    with urlopen(request, timeout=5) as response:
                        return json.loads(response.read())
                except HTTPError as error:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"{route} returned HTTP {error.code}: {detail}") from error

            assert call("/api/state")["agents"] == []
            codex = user / ".codex"
            codex.mkdir(parents=True)
            original_config = 'notify = ["existing-notify.exe"]\n[mcp_servers.keep]\ncommand = "example.exe"\n'
            (codex / "config.toml").write_text(original_config, encoding="utf-8")
            original_hooks = b'{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"other-hook.exe"}]}]}}'
            (codex / "hooks.json").write_bytes(original_hooks)
            for profile in ("desktop", "web"):
                patch = user / ".dsh/profiles" / profile / "cordis.patch.yml"
                patch.parent.mkdir(parents=True)
                patch.write_text("# keep existing profile\n", encoding="utf-8")
            checked = []
            for client in ("codex", "dsh", "custom", "work"):
                payload = {"client": client, "name": "隔离验收"}
                if client == "custom":
                    payload.update({"agent_identity": "Claude", "software": "Obsidian"})
                plan = call("/api/agents/plan", payload)
                prompt = plan["guide"]["prompt"]
                assert plan["handoff"] and not plan["files"] and "plan_id" not in plan
                assert "export" not in plan and "nijika-agent-dialog" in prompt
                assert str(executable.parent / "虹夏MCP-v2/虹夏MCP-v2.exe") in prompt
                if client == "work":
                    assert "保留已有 Work 本机插件" in prompt
                checked.append(client)

            library = user / ".config/magpie/library.json"
            library.parent.mkdir(parents=True)
            original_library = json.dumps({"mcp": [{"name": "nijika-pet", "agents": ["codex"],
                "command": str(executable.parent / "虹夏MCP-v2/虹夏MCP-v2.exe")}]})
            library.write_text(original_library, encoding="utf-8")
            managed = call("/api/agents/plan", {"client": "codex", "name": "已纳管验收"})
            assert managed["manager"] == "magpie" and not managed["files"]
            result = call("/api/agents/apply", {"plan_id": managed["plan_id"]})["agent"]
            assert result["status"] == "managed"
            result = call("/api/agents/prepare", {"id": result["id"]})["agent"]
            assert "本次不授权修改" in result["guide"]["prompt"]
            assert (codex / "config.toml").read_text(encoding="utf-8") == original_config
            assert (codex / "hooks.json").read_bytes() == original_hooks
            assert library.read_text(encoding="utf-8") == original_library
            for profile in ("desktop", "web"):
                assert (user / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(
                    encoding="utf-8") == "# keep existing profile\n"
            assert len(call("/api/state")["agents"]) == 1
            assert not (database.parent / "integrations" / "agents").exists()
            return {"status": "passed", "clients_previewed_in_isolation": checked,
                    "managed_profiles_registered": 1,
                    "api_only": True, "external_client_calls_tested": False,
                    "interaction_preview_included": 'id="page-interaction"' in html}
        finally:
            if process.poll() is None:
                shutdown_file.touch()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        process.kill()
                    process.wait(timeout=5)
                    raise RuntimeError("Isolated panel did not shut down normally")
            if list(temp.glob("_MEI*")):
                raise RuntimeError("Isolated panel left PyInstaller runtime files after shutdown")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, nargs="?", default=ROOT / "dist/虹夏桌宠.exe")
    args = parser.parse_args()
    print(json.dumps(verify(args.executable), ensure_ascii=False))
