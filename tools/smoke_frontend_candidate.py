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
import tomllib
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
        environment = dict(os.environ, NIJIKA_PET_DB_PATH=str(database))
        process = subprocess.Popen(
            [str(executable), "--control-panel", "--serve-only", "--agent-home", str(isolated / "user")],
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
                assert call("/" + name) == (ROOT / "control-ui" / name).read_bytes(), name
            try:
                urlopen(origin + "/api/state", timeout=10)
            except HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError("Unauthenticated candidate API is accessible")
            before = json.loads(call("/api/state"))
            assert before["agents"] == [] and not before["interaction"]["enabled"]
            # Concrete editor entries must survive freezing, with bounded
            # manifest detection and conditional rules rather than global
            # editor labels leaking into the shared backend configuration.
            manifest = isolated / "user/.vscode/extensions/openai.chatgpt-1.0/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"publisher":"openai","name":"chatgpt"}', encoding="utf-8")
            discovered = json.loads(call("/api/agents/scan", {}))
            assert "隔离" in discovered["scope"]
            editor = next(item for item in discovered["clients"] if item.get("extension_id") == "openai.chatgpt")
            assert editor["identity"] == "Codex" and editor["software"] == "VS Code"
            editor_plan = json.loads(call("/api/agents/plan", {
                "client": "custom", "name": "Editor route", "location": str(isolated / "user"),
                "agent_identity": "Codex", "software": "VS Code"}))
            assert "VS Code · Codex" in "\n".join(editor_plan["notes"])
            assert len(editor_plan["files"]) == 1
            assert 'agent_name="Codex"' in editor_plan["guide"]["prompt"]
            assert "不得覆盖共享配置" in editor_plan["guide"]["prompt"]
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
            plan = json.loads(call("/api/agents/plan", {"client": "custom", "name": "Candidate test",
                                                       "agent_identity": "Claude", "software": "VS Code"}))
            applied = json.loads(call("/api/agents/apply", {"plan_id": plan["plan_id"]}))
            assert applied["agent"]["status"] == "exported"
            assert len(json.loads(call("/api/state"))["agents"]) == 1
            identity = plan["export"]["mcpServers"]["nijika-pet"]["env"]
            assert identity == {"NIJIKA_AGENT_NAME": "Claude", "NIJIKA_HOST_NAME": "VS Code",
                                "NIJIKA_PROFILE_ID": applied["agent"]["id"]}
            assert applied["agent"]["export"] == plan["export"]
            assert json.loads(call("/api/agents/export/" + applied["agent"]["id"]))["config"] == plan["export"]
            try:
                call("/api/agents/plan", {"client": "custom", "name": "Missing host"})
            except HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError("Missing custom software was accepted")
            # Exercise the reviewed adapters in the frozen runtime, not just source tests.
            client_home = isolated / "user"
            codex = client_home / ".codex/config.toml"
            codex.parent.mkdir(parents=True)
            mcp_path = plan["export"]["mcpServers"]["nijika-pet"]["command"]
            codex.write_text('[mcp_servers.nijika_pet]\ncommand = ' + json.dumps(mcp_path) +
                             '\nenabled = false\n[mcp_servers.other]\ncommand = "other.exe"\n', encoding="utf-8")
            config_plan = json.loads(call("/api/agents/plan", {"client": "codex", "name": "Codex"}))
            call("/api/agents/apply", {"plan_id": config_plan["plan_id"]})
            servers = tomllib.loads(codex.read_text(encoding="utf-8"))["mcp_servers"]
            assert set(servers) == {"nijika-pet", "other"} and servers["nijika-pet"]["enabled"] is False
            assert servers["other"] == {"command": "other.exe"}
            assert not json.loads(call("/api/agents/plan", {"client": "codex", "name": "Codex"}))["files"]
            sibling = "    - id: unrelated-service\n      name: keep-this-service\n      config: {}\n"
            for profile in ("desktop", "web"):
                patch = client_home / ".dsh/profiles" / profile / "cordis.patch.yml"
                patch.parent.mkdir(parents=True)
                patch.write_text("- insert:\n    - id: magpie-mcp-nijika-pet\n"
                                 "      config:\n        serverName: nijika_pet\n" + sibling, encoding="utf-8")
            dsh_plan = json.loads(call("/api/agents/plan", {"client": "dsh", "name": "DSH"}))
            call("/api/agents/apply", {"plan_id": dsh_plan["plan_id"]})
            for profile in ("desktop", "web"):
                value = (client_home / ".dsh/profiles" / profile / "cordis.patch.yml").read_text(encoding="utf-8")
                assert sibling in value and "magpie-mcp-nijika-pet" not in value
            assert not json.loads(call("/api/agents/plan", {"client": "dsh", "name": "DSH"}))["files"]
            discovered = json.loads(call("/api/agents/scan", {}))
            assert {"codex", "work", "dsh", "claude", "gemini", "copilot"} <= {
                item["id"] for item in discovered["clients"]}
            batch = json.loads(call("/api/agents/batch-plan", {"clients": ["claude", "gemini", "copilot"]}))
            assert all(item["status"] == "ready" for item in batch["results"])
            result = json.loads(call("/api/agents/batch-apply", {"batch_id": batch["batch_id"]}))
            assert all(item["status"] == "configured" for item in result["results"])
            assert all(not item["host_activity"]["called"] for item in json.loads(call("/api/state"))["agents"])
            assert json.loads((client_home / ".copilot/mcp-config.json").read_text())["mcpServers"]["nijika-pet"]["type"] == "local"
            manager = client_home / ".config/magpie/library.json"
            manager.parent.mkdir(parents=True)
            manager.write_text(json.dumps({"mcp":[{"command":mcp_path,"agents":["gemini"]}]}), encoding="utf-8")
            managed = json.loads(call("/api/agents/plan", {"client":"gemini","name":"Managed Gemini"}))
            assert managed["manager"] == "magpie" and not managed["files"]
            assert json.loads(call("/api/agents/apply", {"plan_id":managed["plan_id"]}))["agent"]["status"] == "managed"
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
            assert all("capabilities" in client for client in json.loads(call("/api/state"))["clients"])
            call("/api/support", {"name": "Isolated test", "message": "Test only",
                                  "url": "https://example.com/sponsor"})
            with ZipFile(io.BytesIO(call("/api/support/export"))) as archive:
                assert archive.namelist() == ["distribution/support.json"]
                assert json.loads(archive.read("distribution/support.json"))["name"] == "Isolated test"
            assert database.is_file()
        finally:
            # The onefile bootstrap owns the child app: terminate that owned tree.
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process.terminate()
            process.wait(timeout=15)
    print("Frozen assets, auth, care, Agent export/capabilities, animated skin import/playback and public sponsor export: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    verify(parser.parse_args().executable.resolve())
