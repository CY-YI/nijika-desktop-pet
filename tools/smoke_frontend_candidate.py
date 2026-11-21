"""Verify a frozen settings app in an isolated home, without installing it."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import tempfile
import time
from zipfile import ZipFile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def verify(executable: Path) -> None:
    if not executable.is_file():
        raise FileNotFoundError(executable)
    with tempfile.TemporaryDirectory(prefix="nijika-frozen-frontend-") as directory:
        isolated = Path(directory)
        database = isolated / "state" / "notifications.sqlite3"
        shutdown_file = isolated / "shutdown.signal"
        temp = isolated / "temp"
        temp.mkdir()
        environment = dict(os.environ, NIJIKA_PET_DB_PATH=str(database), TEMP=str(temp), TMP=str(temp))
        process = subprocess.Popen(
            [str(executable), "--control-panel", "--serve-only", "--agent-home", str(isolated / "user"),
             "--test-shutdown-file", str(shutdown_file)],
            env=environment, cwd=executable.parent,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            status_file = database.parent / "panel-status.json"
            deadline = time.monotonic() + 30
            while not status_file.is_file():
                if process.poll() is not None:
                    raise RuntimeError(f"Candidate exited before startup: {process.returncode}")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Candidate did not start its local settings service")
                time.sleep(0.1)
            origin = json.loads(status_file.read_text(encoding="utf-8"))["url"]
            with urlopen(origin, timeout=10) as response:
                html = response.read()
                assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            token = re.search(rb'name="nijika-token" content="([^"]+)"', html).group(1).decode()
            assert html.index(b"/form-state.js") < html.index(b"/app.js") < html.index(b"/interaction.js")

            def call(route: str, data: dict | None = None):
                request = Request(
                    origin + route, json.dumps(data).encode() if data is not None else None,
                    headers={"X-Nijika-Token": token},
                )
                with urlopen(request, timeout=30) as response:
                    return response.read()

            for name in ("form-state.js", "app.js", "interaction.js", "styles.css"):
                # Git archives use LF; reviewed Windows builds may embed CRLF.
                # Compare text with only that transport difference normalized.
                assert call("/" + name).replace(b"\r\n", b"\n") == (
                    ROOT / "control-ui" / name
                ).read_bytes().replace(b"\r\n", b"\n"), name
            try:
                urlopen(origin + "/api/state", timeout=10)
            except HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError("Unauthenticated candidate API is accessible")
            before = json.loads(call("/api/state"))
            assert before["agents"] == [] and not before["interaction"]["enabled"]
            # Detect an editor without modifying its backend or creating a second service.
            client_home = isolated / "user"
            manifest = client_home / ".vscode/extensions/openai.chatgpt-1.0/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"publisher":"openai","name":"chatgpt"}', encoding="utf-8")
            discovered = json.loads(call("/api/agents/scan", {}))
            assert "隔离" in discovered["scope"]
            editor = next(item for item in discovered["clients"] if item.get("extension_id") == "openai.chatgpt")
            assert editor["identity"] == "Codex" and editor["software"] == "VS Code"
            editor_plan = json.loads(call("/api/agents/plan", {
                "client": "custom", "name": "Editor route", "location": str(client_home),
                "agent_identity": "Codex", "software": "VS Code", "via_magpie": False}))
            assert editor_plan["handoff"] and "plan_id" not in editor_plan and not editor_plan["files"]
            assert "VS Code · Codex" in "\n".join(editor_plan["notes"])
            assert 'agent_name="Codex"' in editor_plan["guide"]["prompt"]
            assert "nijika-agent-dialog" in editor_plan["guide"]["prompt"]
            assert "export" not in editor_plan and not (client_home / ".codex").exists()
            saved = json.loads(call("/api/interaction", {
                "enabled": True, "touch_enabled": False, "effects_enabled": False,
            }))
            assert saved["enabled"] and not saved["touch_enabled"] and not saved["effects_enabled"]
            fed = json.loads(call("/api/interaction", {"action": "feed"}))
            assert 99 < fed["care"]["satiety"] <= 100 and fed["care"]["feed_wait"] > 0
            reloaded = json.loads(call("/api/state"))["interaction"]
            assert reloaded["feed_wait"] > 0 and reloaded["drink_wait"] == 0
            assert not reloaded["touch_enabled"] and not reloaded["effects_enabled"]
            preview = call("/api/interaction-preview/pet.webp?strength=gentle&effects=0")
            with Image.open(io.BytesIO(preview)) as image:
                assert image.is_animated and image.n_frames > 30
                assert image.size == (256, 384)
            try:
                call("/api/agents/plan", {"client": "custom", "name": "Missing host"})
            except HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError("Missing custom software was accepted")
            handoff = json.loads(call("/api/agents/plan", {"client": "dsh", "name": "DSH"}))
            assert handoff["handoff"] and not handoff["files"] and "plan_id" not in handoff
            assert handoff["guide"]["prompt"].startswith("本次请通过本机 MAGPIE")
            assert not (client_home / ".dsh").exists()
            for route in ("/api/agents/batch-plan", "/api/agents/batch-apply"):
                try:
                    call(route, {})
                except HTTPError as error:
                    assert error.code == 400
                else:
                    raise AssertionError(f"Direct batch route remained active: {route}")
            manager = client_home / ".config/magpie/library.json"
            manager.parent.mkdir(parents=True)
            mcp_path = str(executable.parent / "虹夏MCP-v2/虹夏MCP-v2.exe")
            assigned = json.dumps({"mcp": [{"name": "nijika-pet", "command": mcp_path, "agents": ["gemini"]}]})
            manager.write_text(assigned, encoding="utf-8")
            guard = client_home / ".gemini/settings.json"
            guard.parent.mkdir(parents=True)
            guard.write_bytes(b'{"untouched":true}')
            managed = json.loads(call("/api/agents/plan", {"client": "gemini", "name": "Managed Gemini"}))
            assert managed["manager"] == "magpie" and not managed["files"]
            profile = json.loads(call("/api/agents/apply", {"plan_id": managed["plan_id"]}))["agent"]
            assert profile["status"] == "managed" and "本次不授权修改" in profile["guide"]["prompt"]
            assert manager.read_text(encoding="utf-8") == assigned and guard.read_bytes() == b'{"untouched":true}'
            assert "export" not in profile and not (database.parent / "integrations" / "agents").exists()
            try:
                call("/api/agents/export/" + profile["id"])
            except HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError("Settings exposed a direct configuration export")
            template = call("/api/skins/template")
            with ZipFile(io.BytesIO(template)) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                assert len(manifest["idle"]["frames"]) == 2
            request = Request(origin + "/api/skins/import", template, headers={
                "X-Nijika-Token": token, "X-Filename": "template.zip",
            })
            with urlopen(request, timeout=30) as response:
                imported = json.loads(response.read())
            assert imported["kind"] == "animated"
            selected = json.loads(call("/api/settings", {"skin": imported["id"]}))
            assert selected["skin"] == imported["id"]
            with Image.open(io.BytesIO(call("/skin/" + imported["id"] + "/idle.webp"))) as image:
                assert image.is_animated and image.n_frames == 2
                assert image.size == (256, 384)
                image.seek(1)
                image.load()
            assert json.loads(call("/api/skins/remove", {"id": imported["id"]}))["reset_to_default"]
            wardrobe = json.loads(call("/api/state"))
            assert wardrobe["settings"]["skin"] == "default"
            assert all(skin["id"] != imported["id"] for skin in wardrobe["skins"])
            demo = json.loads(call("/api/notices/demo-text", {}))
            assert demo["status"] == "pending" and demo["request_id"]
            assert json.loads(call("/api/notices/demo-text", {}))["request_id"] == demo["request_id"]
            assert all("capabilities" in client for client in json.loads(call("/api/state"))["clients"])
            call("/api/support", {"name": "Isolated test", "message": "Test only",
                                  "url": "https://example.com/sponsor"})
            with ZipFile(io.BytesIO(call("/api/support/export"))) as archive:
                names = archive.namelist()
                assert "distribution/support.json" in names
                assert set(names) <= {"distribution/support.json", "distribution/support.png"}
                config = json.loads(archive.read("distribution/support.json"))
                assert config["name"] == "Isolated test"
                if "distribution/support.png" in names:
                    import hashlib
                    assert config["image_sha256"] == hashlib.sha256(
                        archive.read("distribution/support.png")).hexdigest()
            assert database.is_file()
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
    print("Frozen assets, auth, care, MAGPIE, animated skin import/playback/removal, reply demo and sponsor export: OK")


def verify_native_window(executable: Path) -> None:
    for open_at_launch in (True, False):
        with tempfile.TemporaryDirectory(prefix="nijika-native-panel-") as directory:
            root = Path(directory)
            environment = dict(os.environ, NIJIKA_PET_DB_PATH=str(root / "notifications.sqlite3"))
            command = [str(executable), "--demo-seconds", "16"]
            if open_at_launch:
                command.append("--control-panel")
            pet = subprocess.Popen(command, env=environment, cwd=executable.parent)

            def wait_for_status(name: str, key: str) -> dict:
                deadline = time.monotonic() + 12
                while pet.poll() is None and time.monotonic() < deadline:
                    try:
                        state = json.loads((root / name).read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        time.sleep(0.1)
                        continue
                    if state.get(key):
                        return state
                    time.sleep(0.1)
                raise AssertionError(f"Native panel did not report {key} in {name}")

            try:
                if not open_at_launch:
                    wait_for_status("renderer-status.json", "pid")
                    requester = subprocess.run([str(executable), "--control-panel"],
                                               env=environment, cwd=executable.parent, timeout=8)
                    assert requester.returncode == 0
                panel = wait_for_status("panel-status.json", "view_ready")
                assert panel["pid"] == pet.pid, panel
            finally:
                try:
                    pet.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    pet.terminate()
                    pet.wait(timeout=5)
                    raise RuntimeError("Isolated pet did not shut down normally")
            assert pet.returncode == 0
            assert not (root / "panel-status.json").exists()
    print("WebView rendered settings both at launch and from an already running pet: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--native-window", action="store_true", help="also verify content in native WebView2")
    args = parser.parse_args()
    executable = args.executable.resolve()
    verify(executable)
    if args.native_window:
        verify_native_window(executable)
