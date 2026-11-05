"""Explicitly export or package only public sponsor information, never the user database."""
from __future__ import annotations

import io
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

DEFAULT_SUPPORT = {"name": "虹夏桌宠的开发者", "message": "谢谢你喜欢这个小小的陪伴。", "url": ""}


def application_directory() -> Path:
    return Path(sys.executable).resolve().parent.parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def validate_support(config: dict) -> dict:
    if (not isinstance(config, dict) or set(config) != {"name", "message", "url"}
            or not all(isinstance(value, str) for value in config.values())):
        raise ValueError("请填写作者名、说明和可选支持链接。")
    if not 1 <= len(config["name"].strip()) <= 40 or len(config["message"]) > 200:
        raise ValueError("作者名限 1–40 字，说明限 200 字。")
    try:
        url = urlsplit(config["url"])
        if config["url"] and (len(config["url"]) > 2048 or url.scheme != "https"
                              or not url.hostname or url.username or url.password
                              or any(ord(char) < 33 for char in config["url"])):
            raise ValueError("支持链接必须是完整的 HTTPS 地址。")
    except ValueError as error:
        raise ValueError("支持链接必须是完整的 HTTPS 地址。") from error
    return dict(config)


def load_public_support(root: Path) -> dict:
    path = root / "distribution" / "support.json"
    try:
        if path.stat().st_size > 8192:
            return dict(DEFAULT_SUPPORT)
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return dict(DEFAULT_SUPPORT)
        document.pop("image_sha256", None)
        return validate_support(document)
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_SUPPORT)


def public_support_image(root: Path) -> Path | None:
    try:
        path = root / "distribution/support.png"
        document = root / "distribution/support.json"
        if path.stat().st_size > 8 * 1024 * 1024 or document.stat().st_size > 8192:
            return None
        config = json.loads(document.read_text(encoding="utf-8"))
        digest = config.pop("image_sha256", None)
        validate_support(config)
        if digest and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            return path
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def read_public_bundle(root: Path) -> dict[str, bytes]:
    """Read reviewed public sponsor files and fail closed on inconsistent data."""
    document = root / "distribution" / "support.json"
    image_path = root / "distribution" / "support.png"
    if not document.is_file():
        if image_path.exists():
            raise ValueError("公开赞助资料缺少 support.json，不能单独打包收款图。")
        return {}
    if document.stat().st_size > 8192:
        raise ValueError("公开赞助说明过大。")
    try:
        config = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("无法读取公开赞助说明。") from error
    if not isinstance(config, dict):
        raise ValueError("公开赞助说明需要 JSON 对象。")
    digest = config.pop("image_sha256", None)
    config = validate_support(config)
    image = None
    if image_path.is_file():
        if image_path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("公开赞助图片不能超过 8 MB。")
        image = image_path.read_bytes()
        if digest and hashlib.sha256(image).hexdigest() != digest:
            raise ValueError("公开赞助图片与说明中的摘要不匹配。")
    return read_bundle(export_bundle(config, image))


def export_bundle(config: dict, image: bytes | None) -> bytes:
    config = validate_support(config)
    if not config["url"] and not image:
        raise ValueError("请先保存真实的赞助链接或收款图片，再导出发布资料。")
    if image:
        config["image_sha256"] = hashlib.sha256(image).hexdigest()
    result = io.BytesIO()
    with ZipFile(result, "w", ZIP_DEFLATED) as archive:
        archive.writestr("distribution/support.json", json.dumps(config, ensure_ascii=False, indent=2))
        if image:
            archive.writestr("distribution/support.png", image)
    return result.getvalue()


def read_bundle(data: bytes) -> dict[str, bytes]:
    from control_store import ControlStore
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("赞助资料不能超过 8 MB。")
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            allowed = {"distribution/support.json", "distribution/support.png"}
            if (len(names) != len(set(names)) or set(names) - allowed
                    or "distribution/support.json" not in names
                    or sum(item.file_size for item in archive.infolist()) > 8 * 1024 * 1024):
                raise ValueError("赞助包只能包含公开说明 JSON 与可选收款 PNG。")
            raw = archive.read("distribution/support.json")
            if len(raw) > 8192:
                raise ValueError("赞助说明过大。")
            document = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError("赞助说明需要 JSON 对象。")
            document.pop("image_sha256", None)
            config = validate_support(document)
            result = {}
            image = None
            if "distribution/support.png" in names:
                source = ControlStore.read_image(archive.read("distribution/support.png"), transparent=False)
                buffer = io.BytesIO()
                source.save(buffer, format="PNG")
                image = buffer.getvalue()
                result["distribution/support.png"] = image
                config["image_sha256"] = hashlib.sha256(image).hexdigest()
            if not image and not config["url"]:
                raise ValueError("赞助包需要真实链接或图片。")
            result["distribution/support.json"] = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
            return result
    except (BadZipFile, UnicodeError, KeyError) as error:
        raise ValueError("无法读取赞助发布资料。") from error
