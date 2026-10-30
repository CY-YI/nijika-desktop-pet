"""Check the frozen settings/Agent handoff against disposable local data.

This exercises the API, not browser layout or external clients' autonomous calls.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
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
        environment = {**os.environ, "NIJIKA_PET_DB_PATH": str(database)}
        process = subprocess.Popen(
            [str(executable), "--control-panel", "--serve-only", "--agent-home", str(user)],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        panel_pid = None
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
            panel_pid = panel["pid"]
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
            for client in ("codex", "dsh", "custom"):
                payload = {"client": client, "name": "隔离验收"}
                if client == "custom":
                    payload.update({"agent_identity": "Claude", "software": "Obsidian"})
                plan = call("/api/agents/plan", payload)
                assert "wait_for_reply" in plan["instructions"]
                assert "# BEGIN NIJIKA-CODEX-DIALOG" not in plan["instructions"]
                result = call("/api/agents/apply", {"plan_id": plan["plan_id"]})["agent"]
                result = call("/api/agents/prepare", {"id": result["id"]})["agent"]
                bundle = Path(result["bundle_directory"])
                assert bundle.is_relative_to(isolated)
                config = json.loads((bundle / "nijika-mcp.json").read_text(encoding="utf-8"))
                assert config["mcpServers"]["nijika-pet"]["command"] == str(executable.parent / "虹夏MCP-v2.exe")
                prompt = (bundle / "nijika-setup-prompt.txt").read_text(encoding="utf-8")
                assert prompt == result["guide"]["prompt"]
                assert "status=invalid" in prompt and "20显示列" in prompt
                for item in result["needed_files"]:
                    assert Path(item["path"]).is_absolute() and item["path"] in prompt
                if client == "codex":
                    assert (codex / "config.toml").read_text(encoding="utf-8").startswith(original_config.rstrip())
                    assert (codex / "hooks.json").read_bytes() == original_hooks
                    assert "UserPromptSubmit、PermissionRequest、PostToolUse、Stop" in prompt
                if client == "dsh":
                    assert "尚未实现 DSH 宿主原生权限" in prompt
                    for profile in ("desktop", "web"):
                        saved = (user / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
                        assert saved.startswith("# keep existing profile") and saved.count("id: mcp-nijika-pet") == 1
                checked.append(client)
            assert len(call("/api/state")["agents"]) == len(checked)
            return {"status": "passed", "clients_applied_in_isolation": checked,
                    "api_only": True, "external_client_calls_tested": False,
                    "interaction_preview_included": 'id="page-interaction"' in html}
        finally:
            if panel_pid is not None and panel_pid != process.pid:
                try:
                    os.kill(panel_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                if panel_pid == process.pid:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, nargs="?", default=ROOT / "dist/虹夏桌宠.exe")
    args = parser.parse_args()
    print(json.dumps(verify(args.executable), ensure_ascii=False))
