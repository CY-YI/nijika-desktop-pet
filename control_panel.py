"""Local, authenticated management API and WebView2 desktop settings window."""
from __future__ import annotations

import argparse
import hmac
import io
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image

from agent_setup import AgentSetup
from companion_store import CompanionStore
from control_store import ControlStore, IDENTIFIER, SPRITES
from notification_store import NotificationStore
from interaction_store import InteractionStore
from interaction_motion import ACTIONS, preview_webp


WINDOW_TITLE = "虹夏桌宠 · 设置中心"
_preview_lock = threading.Lock()


@lru_cache(maxsize=4)
def skin_idle_preview(directory: str) -> bytes:
    from skin_animation import SkinTimeline
    timeline = SkinTimeline.load(Path(directory))
    if not timeline.animation:
        raise ValueError("这个皮肤没有待机帧。")
    frames = []
    for filename in timeline.animation["frames"]:
        with Image.open(Path(directory) / filename) as source:
            image = source.convert("RGBA")
            image.thumbnail((256, 384), Image.Resampling.LANCZOS)
            frames.append(image)
    output = io.BytesIO()
    frames[0].save(output, format="WEBP", save_all=True, append_images=frames[1:],
                   duration=timeline.animation["durations_ms"], loop=0, lossless=True)
    return output.getvalue()


@lru_cache(maxsize=8)
def interaction_preview(directory: str, action: str, strength: str, effects: bool) -> bytes:
    with Image.open(Path(directory) / (ACTIONS[action][2] + ".png")) as image:
        art = image.convert("RGBA")
        art.thumbnail((236, 354), Image.Resampling.LANCZOS)
    source = Image.new("RGBA", (256, 384))
    source.alpha_composite(art, ((256 - art.width) // 2, (384 - art.height) // 2))
    return preview_webp(source, action, 0.5 if strength == "gentle" else 1.0, effects)


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def application_root() -> Path:
    return Path(sys.executable).resolve().parent.parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


class ControlApplication:
    def __init__(self, database: Path | None = None, root: Path | None = None, home: Path | None = None):
        self.store = ControlStore(database, public_root=root or application_root())
        self.notifications = NotificationStore(self.store.database)
        self.companion = CompanionStore(self.store.database)
        self.interaction = InteractionStore(self.store.database)
        self.root = root or application_root()
        self.setup = AgentSetup(self.root, self.store, home)

    def renderer(self) -> dict:
        try:
            status = json.loads((self.store.root / "renderer-status.json").read_text(encoding="utf-8"))
            age = time.time() - status.get("heartbeat_at", 0)
            online = 0 <= age < 12
            return {"online": online, "active_notice_id": status.get("active_notice_id"),
                    "window_visible": bool(status.get("window_visible")),
                    "supports_control": bool(status.get("supports_control")),
                    "desktop_playback": bool(online and status.get("desktop_playback")),
                    "interaction_action": status.get("interaction_action") if online else None,
                    "applied_revision": status.get("applied_revision", -1)}
        except (OSError, ValueError, TypeError):
            return {"online": False, "window_visible": False, "supports_control": False,
                    "desktop_playback": False, "interaction_action": None, "applied_revision": -1}

    def notice(self, request_id: str) -> dict:
        if not IDENTIFIER.fullmatch(request_id):
            raise ValueError("提醒编号无效。")
        item = self.notifications.get(request_id)
        if not item:
            return {"request_id": request_id, "status": "not_found", "visible": False}
        renderer = self.renderer()
        return {**item.result(), "visible": bool(renderer["online"] and renderer["window_visible"] and
                                                 renderer.get("active_notice_id") == request_id)}

    def state(self) -> dict:
        renderer = self.renderer()
        agents = self.store.agents()
        for agent in agents:
            request_id = agent.get("test_request_id")
            agent["test"] = self.notice(request_id) if request_id else None
            agent.update(self.setup.describe(agent))
            # Backups are local recovery artifacts, not useful to every state poll.
            agent.pop("backups", None)
        return {"renderer": renderer, "settings": self.store.settings(), "agents": agents,
                "clients": self.setup.clients(), "skins": self.store.skins(), "support": self.store.support(),
                "companion": self.companion.snapshot(),
                "interaction": {**self.interaction.snapshot(),
                                "desktop_playback": bool(renderer.get("desktop_playback"))}}

    def post(self, route: str, data: dict) -> dict:
        if route == "/api/agents/plan":
            return self.setup.plan(data.get("client"), data.get("name"), data.get("location", ""),
                                   data.get("agent_identity"), data.get("software", ""))
        if route == "/api/agents/apply":
            return self.setup.apply(data.get("plan_id", ""))
        if route == "/api/agents/prepare":
            agent = self.store.agent(data.get("id", ""))
            if not agent:
                raise ValueError("请先添加这个 Agent。")
            return {"agent": {**agent, **self.setup.prepare_files(agent)}}
        if route == "/api/agents/remove":
            self.store.remove_agent(data.get("id", ""))
            return {"removed": True, "message": "已移除面板档案，客户端配置保持不变。"}
        if route == "/api/agents/test":
            agent = self.store.agent(data.get("id", ""))
            if not agent:
                raise ValueError("请先添加这个 Agent。")
            previous = agent.get("test_request_id")
            if previous and self.notice(previous)["status"] == "pending":
                return self.notice(previous)
            identity = self.setup.export_agent(agent)["mcpServers"]["nijika-pet"]["env"]
            notice = self.notifications.create(identity["NIJIKA_AGENT_NAME"], "接入测试",
                        "这是管理面板发送的本机测试提醒。点击后可在面板看到回执；外部 Agent 仍需在新任务中验证调用。", ("收到测试",),
                        software=identity.get("NIJIKA_HOST_NAME", ""))
            agent["test_request_id"] = notice.id
            self.store.save_agent(agent)
            return self.notice(notice.id)
        if route == "/api/settings":
            return self.store.update_settings(data)
        if route == "/api/interaction":
            if "action" in data:
                if set(data) != {"action"} or not isinstance(data["action"], str):
                    raise ValueError("投喂操作只接受一个点心或喝水动作。")
                return self.interaction.feed(data["action"])
            return self.interaction.configure(data)
        if route == "/api/support":
            return self.store.update_support(data)
        if route == "/api/focus":
            action = data.get("action")
            if not isinstance(action, str):
                raise ValueError("请选择专注计时的操作。")
            if action == "configure":
                return self.companion.pomodoro_action("configure",
                                                      focus_minutes=data.get("focus_minutes"),
                                                      break_minutes=data.get("break_minutes"))
            return self.companion.pomodoro_action(action)
        if route == "/api/reminders":
            if "pause_minutes" in data:
                return self.companion.pause_reminders(data["pause_minutes"])
            patch = {key: value for key, value in data.items() if key != "pause_minutes"}
            return self.companion.update_reminders(patch)
        if route == "/api/notes":
            action = data.get("action")
            if action == "add":
                return self.companion.add_note(data.get("text", ""))
            if action == "toggle":
                return self.companion.toggle_note(int(data.get("id", 0)))
            if action == "remove":
                self.companion.remove_note(int(data.get("id", 0)))
                return {"removed": True}
            raise ValueError("不支持的便签操作。")
        if route == "/api/pet/start":
            if self.renderer()["online"]:
                return {"started": False, "message": "虹夏已经在桌面运行。"}
            executable = Path(sys.executable) if getattr(sys, "frozen", False) else self.root / "dist" / "虹夏桌宠.exe"
            if not executable.is_file():
                raise ValueError("找不到桌宠 EXE，请先构建或安装完整程序。")
            subprocess.Popen([str(executable)], cwd=Path(executable).parent,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return {"started": True, "message": "已启动，正在等待桌宠心跳。"}
        raise ValueError("不支持的操作。")


class ControlServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, app: ControlApplication, port: int = 0):
        self.app = app
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), ControlHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


class ControlHandler(BaseHTTPRequestHandler):
    server: ControlServer

    def log_message(self, *_args):
        pass

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def allowed(self, api: bool) -> bool:
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            return False
        origin = self.headers.get("Origin")
        if origin and origin != self.server.origin:
            return False
        if api:
            return hmac.compare_digest(self.headers.get("X-Nijika-Token", "").encode("utf-8"), self.server.token.encode("utf-8"))
        return True

    def do_OPTIONS(self):
        self.send_json({"error": "不开放跨域调用。"}, 403)

    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if not self.allowed(route.startswith("/api/")):
            self.send_json({"error": "此页面的管理会话无效，请重新打开设置窗口。"}, 403)
            return
        try:
            if route == "/api/state":
                self.send_json(self.server.app.state())
            elif route == "/api/support/export":
                self.send_bytes(self.server.app.store.export_support(), "application/zip")
            elif route == "/api/skins/template":
                store = self.server.app.store
                directory = store.skin_directory(store.settings()["skin"]) or resource_root() / "assets/sprites"
                manifest = {"name": "多帧皮肤示例（请替换为自己的角色）", "idle": {
                    "frames": ["idle_000.png", "idle_001.png"], "durations_ms": [1800, 140]}}
                output = io.BytesIO()
                with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
                    for sprite in SPRITES:
                        archive.writestr(sprite + ".png", (directory / (sprite + ".png")).read_bytes())
                    archive.writestr("idle_000.png", (directory / "curious.png").read_bytes())
                    archive.writestr("idle_001.png", (directory / "blink.png").read_bytes())
                self.send_bytes(output.getvalue(), "application/zip")
            elif route.startswith("/api/interaction-preview/"):
                action = route.rsplit("/", 1)[-1].removesuffix(".webp")
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if action not in ACTIONS or route != f"/api/interaction-preview/{action}.webp":
                    raise ValueError("不支持这个互动动作。")
                if set(query) - {"strength", "effects", "skin"} or any(len(value) != 1 for value in query.values()):
                    raise ValueError("动作预览参数无效。")
                strength, effects = query.get("strength", ["lively"])[0], query.get("effects", ["1"])[0]
                if strength not in ("gentle", "lively") or effects not in ("0", "1"):
                    raise ValueError("请选择轻柔或活泼幅度，以及是否显示特效。")
                skin = query.get("skin", [self.server.app.store.settings()["skin"]])[0]
                directory = self.server.app.store.skin_directory(skin) or resource_root() / "assets" / "sprites"
                # Serialize only expensive preview generation; other API requests stay responsive.
                with _preview_lock:
                    data = interaction_preview(str(directory), action, strength, effects == "1")
                self.send_bytes(data, "image/webp")
            elif route.startswith("/api/notices/"):
                self.send_json(self.server.app.notice(route.rsplit("/", 1)[1]))
            elif route.startswith("/api/agents/export/"):
                agent = self.server.app.store.agent(route.rsplit("/", 1)[1])
                if not agent:
                    raise ValueError("找不到 Agent 档案。")
                self.send_json({"config": self.server.app.setup.export_agent(agent),
                                "instructions": (self.server.app.root / "distribution/codex-global-instructions.txt").read_text(encoding="utf-8-sig")})
            elif route in ("/", "/app.js", "/form-state.js", "/interaction.js", "/styles.css"):
                filename = "index.html" if route == "/" else route[1:]
                data = (resource_root() / "control-ui" / filename).read_bytes()
                if filename == "index.html":
                    data = data.replace(b"NIJIKA_SESSION_TOKEN", self.server.token.encode("ascii"))
                content_type = "text/javascript; charset=utf-8" if filename.endswith(".js") else {"index.html": "text/html; charset=utf-8", "styles.css": "text/css; charset=utf-8"}[filename]
                self.send_bytes(data, content_type)
            elif route.startswith("/skin/"):
                parts = route.strip("/").split("/")
                if len(parts) != 3:
                    raise ValueError("角色图片路径无效。")
                directory = self.server.app.store.skin_directory(parts[1]) or resource_root() / "assets" / "sprites"
                if parts[2] == "idle.webp":
                    with _preview_lock:
                        data = skin_idle_preview(str(directory))
                    self.send_bytes(data, "image/webp")
                    return
                from skin_animation import SkinTimeline
                idle = (SkinTimeline.load(directory).animation or {}).get("frames", [])
                if parts[2] not in {f"{item}.png" for item in SPRITES} | set(idle):
                    raise ValueError("角色图片路径无效。")
                self.send_bytes((directory / parts[2]).read_bytes(), "image/png")
            elif route == "/support/qr.png":
                image = self.server.app.store.support_image()
                if image is None:
                    raise ValueError("尚未配置有效的收款图片。")
                self.send_bytes(image.read_bytes(), "image/png")
            else:
                self.send_json({"error": "页面不存在。"}, 404)
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except (OSError, sqlite3.Error):
            self.send_json({"error": "暂时无法读取本机数据，请重试。"}, 503)

    def do_POST(self):
        route = urlsplit(self.path).path
        if not self.allowed(True):
            self.send_json({"error": "管理会话无效或请求来自其他网站。"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            limit = 32 * 1024 * 1024 if route == "/api/skins/import" else 8 * 1024 * 1024 if route == "/api/support/image" else 64 * 1024
            if not 0 < length <= limit:
                raise ValueError("请求为空或文件超过大小限制。")
            self.connection.settimeout(15)
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("文件未完整上传，请重试。")
            if route == "/api/skins/import":
                result = self.server.app.store.import_skin(body, unquote(self.headers.get("X-Filename", "skin.png")))
            elif route == "/api/support/image":
                self.server.app.store.save_support_image(body)
                result = self.server.app.store.support()
            else:
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ValueError("请求需要是一个设置对象。")
                result = self.server.app.post(route, payload)
            self.send_json(result)
        except (ValueError, TypeError, UnicodeDecodeError) as error:
            self.send_json({"error": str(error)}, 400)
        except (OSError, sqlite3.Error):
            self.send_json({"error": "本机文件或数据暂时不可用，请检查目录权限与客户端状态后重试。"}, 503)


def run_panel(argv: list[str] | None = None) -> None:
    """Start the local management service and its WebView2 window.

    Called both by this module's ``main`` and by ``pet.py --control-panel`` so the
    desktop companion and its settings live in a single executable.
    """
    parser = argparse.ArgumentParser(description="虹夏桌宠 · 设置与 Agent 接入")
    parser.add_argument("--browser", action="store_true", help="在浏览器打开面板")
    parser.add_argument("--serve-only", action="store_true", help="仅启动本机服务，供开发和隔离验证")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--agent-home", type=Path, help="隔离测试用的客户端用户目录")
    args = parser.parse_args(argv)
    app = ControlApplication(home=args.agent_home)
    server = ControlServer(app, args.port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    status = app.store.root / "panel-status.json"
    status.write_text(json.dumps({"pid": os.getpid(), "url": server.origin}, ensure_ascii=False), encoding="utf-8")
    try:
        if sys.stdout:
            print(server.origin, flush=True)
    except (OSError, ValueError):
        pass
    try:
        if args.serve_only:
            thread.join()
        elif args.browser:
            webbrowser.open(server.origin)
            thread.join()
        else:
            import webview
            webview.create_window(WINDOW_TITLE, server.origin, width=1220, height=820, min_size=(950, 680))
            webview.start(gui="edgechromium", debug=False, private_mode=True)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        try:
            if json.loads(status.read_text(encoding="utf-8")).get("pid") == os.getpid():
                status.unlink()
        except (OSError, ValueError):
            pass


def main():
    run_panel()


if __name__ == "__main__":
    main()
