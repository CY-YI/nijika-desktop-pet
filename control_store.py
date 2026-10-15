"""Persistent, local-only preferences and image packs for the control panel."""
from __future__ import annotations

import io
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from PIL import Image, UnidentifiedImageError
from notification_store import default_database_path

EXPRESSIONS = ("curious", "happy", "worried", "sleepy", "wink", "thinking", "pout", "excited")
SPRITES = (*EXPRESSIONS, "blink")
DEFAULTS = {"width": 320, "motion": "lively", "expression": "curious",
            "chat_enabled": True, "skin": "default"}
IDENTIFIER = re.compile(r"^[a-f0-9]{32}$")


class ControlStore:
    def __init__(self, database: Path | None = None):
        self.database = database or default_database_path()
        self.root = self.database.parent
        self.root.mkdir(parents=True, exist_ok=True)
        connection = self.connect()
        try:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS panel_preferences (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS panel_agents (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        finally:
            connection.close()

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=2)
        return connection

    def document(self, key: str, default: dict) -> dict:
        connection = self.connect()
        try:
            row = connection.execute("SELECT value FROM panel_preferences WHERE name=?", (key,)).fetchone()
            return json.loads(row[0]) if row else dict(default)
        finally:
            connection.close()

    def settings(self) -> dict:
        return self.document("settings", {**DEFAULTS, "revision": 0})

    def update_settings(self, patch: dict) -> dict:
        if set(patch) - set(DEFAULTS):
            raise ValueError("包含不支持的设置项。")
        if "width" in patch and (type(patch["width"]) is not int or patch["width"] not in (260, 320, 380)):
            raise ValueError("角色大小必须为小号、中号或大号。")
        if "motion" in patch and patch["motion"] not in ("lively", "gentle", "off"):
            raise ValueError("请选择有效的动作强度。")
        if "expression" in patch and patch["expression"] not in EXPRESSIONS:
            raise ValueError("请选择有效的表情。")
        if "chat_enabled" in patch and type(patch["chat_enabled"]) is not bool:
            raise ValueError("闲聊设置必须为开或关。")
        if "skin" in patch:
            self.skin_directory(patch["skin"])
        connection = self.connect()
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT value FROM panel_preferences WHERE name='settings'").fetchone()
                current = json.loads(row[0]) if row else {**DEFAULTS, "revision": 0}
                current.update(patch)
                current["revision"] += 1
                connection.execute("INSERT OR REPLACE INTO panel_preferences VALUES ('settings', ?)",
                                   (json.dumps(current, ensure_ascii=False),))
            return current
        finally:
            connection.close()

    def agents(self) -> list[dict]:
        connection = self.connect()
        try:
            return [json.loads(row[0]) for row in connection.execute("SELECT value FROM panel_agents ORDER BY rowid")]
        finally:
            connection.close()

    def agent(self, agent_id: str) -> dict:
        return next((item for item in self.agents() if item["id"] == agent_id), {})

    def save_agent(self, item: dict) -> dict:
        connection = self.connect()
        try:
            with connection:
                connection.execute("INSERT OR REPLACE INTO panel_agents VALUES (?, ?)",
                                   (item["id"], json.dumps(item, ensure_ascii=False)))
            return item
        finally:
            connection.close()

    def remove_agent(self, agent_id: str) -> None:
        connection = self.connect()
        try:
            with connection:
                connection.execute("DELETE FROM panel_agents WHERE id=?", (agent_id,))
        finally:
            connection.close()

    def skin_directory(self, skin: str) -> Path | None:
        if skin == "default":
            return None
        if not isinstance(skin, str) or not IDENTIFIER.fullmatch(skin):
            raise ValueError("皮肤编号无效。")
        folder = self.root / "skins" / skin
        if not (folder / "manifest.json").is_file() or not all((folder / f"{name}.png").is_file() for name in SPRITES):
            raise ValueError("找不到这个皮肤，请重新导入。")
        return folder

    def skins(self) -> list[dict]:
        result = [{"id": "default", "name": "虹夏 · 经典制服", "kind": "expressions", "builtin": True}]
        for manifest in sorted((self.root / "skins").glob("*/manifest.json")):
            if not IDENTIFIER.fullmatch(manifest.parent.name):
                continue
            try:
                self.skin_directory(manifest.parent.name)
                data = json.loads(manifest.read_text(encoding="utf-8"))
                result.append({"id": manifest.parent.name, "name": str(data["name"])[:40],
                               "kind": data.get("kind", "expressions"), "builtin": False})
            except (OSError, ValueError, KeyError):
                continue
        return result

    @staticmethod
    def read_image(data: bytes, *, transparent: bool = True) -> Image.Image:
        try:
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in (("PNG",) if transparent else ("PNG", "JPEG", "WEBP")):
                    raise ValueError("请选择 PNG 角色图或 PNG/JPEG 收款图片。")
                if source.width * source.height > 8_000_000 or min(source.size) < 32:
                    raise ValueError("图片尺寸过小或超过 800 万像素。")
                image = source.convert("RGBA")
                if transparent:
                    alpha_min, alpha_max = image.getchannel("A").getextrema()
                    if alpha_min != 0 or alpha_max == 0 or image.getpixel((0, 0))[3] != 0:
                        raise ValueError("角色图需要透明背景，并保留可见角色。")
                    if not 0.62 <= image.width / image.height <= 0.72:
                        raise ValueError("角色画布需接近宽高比 2:3，以免桌宠被拉伸。")
                return image
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ValueError("无法读取图片，请检查格式与大小。") from error

    def import_skin(self, data: bytes, filename: str) -> dict:
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("皮肤文件不能超过 32 MB。")
        name = Path(filename).stem.strip()[:40] or "我的皮肤"
        images = {}
        kind = "static"
        if filename.lower().endswith(".zip"):
            kind = "expressions"
            try:
                with ZipFile(io.BytesIO(data)) as archive:
                    entries = [item for item in archive.infolist() if not item.is_dir()]
                    allowed = {f"{sprite}.png" for sprite in SPRITES} | {"manifest.json"}
                    if len(entries) > 10 or sum(item.file_size for item in entries) > 64 * 1024 * 1024:
                        raise ValueError("图片包文件过多或解压体积超过 64 MB。")
                    for item in entries:
                        path = Path(item.filename.replace("\\", "/"))
                        if path.is_absolute() or ".." in path.parts or len(path.parts) > 2 or path.name not in allowed:
                            raise ValueError("皮肤包只能包含九张指定 PNG 和可选 manifest.json。")
                        if path.name == "manifest.json":
                            if item.file_size > 4096:
                                raise ValueError("皮肤清单过大。")
                            manifest = json.loads(archive.read(item))
                            if not isinstance(manifest, dict):
                                raise ValueError("皮肤清单需要是 JSON 对象。")
                            name = str(manifest.get("name", name)).strip()[:40] or name
                        else:
                            sprite = path.stem
                            if sprite in images:
                                raise ValueError("皮肤包中存在重名图片。")
                            images[sprite] = self.read_image(archive.read(item))
                    if set(images) != set(SPRITES) or len({image.size for image in images.values()}) != 1:
                        raise ValueError("皮肤包需要九张同尺寸图片：八种表情与 blink.png。")
            except (BadZipFile, json.JSONDecodeError) as error:
                raise ValueError("皮肤 ZIP 或清单格式无效。") from error
        else:
            image = self.read_image(data)
            images = dict.fromkeys(SPRITES, image)
        skin_id = uuid.uuid4().hex
        folder = self.root / "skins" / skin_id
        folder.mkdir(parents=True)
        for sprite, image in images.items():
            image.save(folder / f"{sprite}.png")
        item = {"id": skin_id, "name": name, "kind": kind, "builtin": False}
        (folder / "manifest.json").write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
        return item

    def support(self) -> dict:
        config = self.document("support", {"name": "虹夏桌宠的开发者", "message": "谢谢你喜欢这个小小的陪伴。", "url": ""})
        return {**config, "has_image": (self.root / "support" / "qr.png").is_file()}

    def update_support(self, patch: dict) -> dict:
        from urllib.parse import urlsplit
        if set(patch) != {"name", "message", "url"} or not all(isinstance(v, str) for v in patch.values()):
            raise ValueError("请填写作者名、说明和可选支持链接。")
        if len(patch["name"]) > 40 or not patch["name"].strip() or len(patch["message"]) > 200:
            raise ValueError("作者名限 1–40 字，说明限 200 字。")
        url = urlsplit(patch["url"])
        if patch["url"] and (len(patch["url"]) > 2048 or url.scheme != "https" or not url.hostname or url.username or url.password):
            raise ValueError("支持链接必须是完整的 HTTPS 地址。")
        connection = self.connect()
        try:
            with connection:
                connection.execute("INSERT OR REPLACE INTO panel_preferences VALUES ('support', ?)",
                                   (json.dumps(patch, ensure_ascii=False),))
        finally:
            connection.close()
        return self.support()

    def save_support_image(self, data: bytes) -> None:
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("收款图片不能超过 8 MB。")
        image = self.read_image(data, transparent=False)
        target = self.root / "support" / "qr.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        image.save(temporary, format="PNG")
        temporary.replace(target)
