"""Preview and apply one Magpie-owned Nijika router change through Magpie's CLI."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from agent_discovery import magpie_state
from app_layout import validate_bundled_mcp


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_magpie_cli() -> Path | None:
    candidates = set()
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", "")
        powershell = Path(system_root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        if system_root and powershell.is_file():
            command = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
                       "Get-CimInstance Win32_Process -Filter \"Name='magpie-windows-amd64.exe'\" "
                       "| Select-Object -ExpandProperty ExecutablePath")
            try:
                result = subprocess.run([str(powershell), "-NoProfile", "-NonInteractive", "-Command", command],
                                        capture_output=True, timeout=8, check=False,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if result.returncode == 0:
                    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
                        if line.strip():
                            candidates.add(Path(line.strip()).resolve())
            except (OSError, subprocess.TimeoutExpired):
                pass
    else:
        found = shutil.which("magpie")
        if found:
            candidates.add(Path(found).resolve())
    candidates = {path for path in candidates if path.is_file() and
                  path.name.casefold() in {"magpie", "magpie.exe", "magpie-windows-amd64.exe"}}
    return next(iter(candidates)) if len(candidates) == 1 else None


class MagpieDirectRoute:
    def __init__(self, home: Path, root: Path, *, use_environment: bool,
                 locate=find_magpie_cli, run=subprocess.run):
        self.home = home
        self.root = root
        self.use_environment = use_environment
        self.locate = locate
        self.run = run
        self.plans: dict[str, dict] = {}
        self.lock = threading.Lock()

    def preview(self, client: str) -> dict:
        if not isinstance(client, str) or not client or len(client) > 80:
            raise ValueError("客户端无效，请重新扫描。")
        mcp = validate_bundled_mcp(self.root)
        state = magpie_state(self.home, client, use_environment=self.use_environment)
        if state["error"] or not state["managed"]:
            raise ValueError("无法确认 MAGPIE 对此客户端的虹夏管理归属，请重新扫描。")
        if state["route"] != "shared":
            raise ValueError("虹夏当前无需从共享路由切换，请重新扫描。")
        if (state["service_name"] not in {"nijika-pet", "nijika_pet"} or
                Path(state["command"]).resolve() != mcp.resolve()):
            raise ValueError("MAGPIE 中的虹夏不是当前安装的已知程序，未进行任何修改。")
        if not state["identity_compatible"] or not state["arguments_compatible"]:
            raise ValueError("MAGPIE 的虹夏来源、档案或启动参数需要先核对，避免影响其他客户端。")
        if (len(state["targets"]) > 100 or len(set(state["targets"])) != len(state["targets"]) or
                any(not target.strip() or len(target) > 80 or any(ord(char) < 32 for char in target) for target in state["targets"])):
            raise ValueError("MAGPIE 的客户端列表无法安全预览，请在 MAGPIE 中核对。")
        result = {"service": state["service_name"], "targets": state["targets"],
                  "can_apply": False, "plan_id": None,
                  "note": "仅请求改变虹夏的路由；MAGPIE 会同步其资源库，可能同时更新其他由它管理的条目。客户端需重连，来源与自动提醒仍需实测。"}
        if not self.use_environment:
            result["note"] += " 隔离预览禁止调用真实 MAGPIE。"
            return result
        executable = self.locate()
        if not executable:
            result["note"] += " 未能唯一定位运行中的 MAGPIE，请在 MAGPIE 界面切换。"
            return result
        try:
            help_result = self.run([str(executable), "library", "help"], capture_output=True, timeout=8, stdin=subprocess.DEVNULL,
                                   check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            help_text = help_result.stdout.decode("utf-8", errors="replace")
            if help_result.returncode or "shared|direct" not in help_text:
                result["note"] += " 当前 MAGPIE 未确认支持此操作，请使用其界面核对。"
                return result
            binary_hash = file_digest(executable)
        except (OSError, subprocess.TimeoutExpired):
            result["note"] += " 无法核对 MAGPIE 程序，请使用其界面核对。"
            return result
        plan_id = uuid.uuid4().hex
        with self.lock:
            self.plans = {key: value for key, value in self.plans.items()
                          if time.monotonic() - value["created"] < 600}
            if len(self.plans) >= 32:
                self.plans.pop(next(iter(self.plans)))
            self.plans[plan_id] = {"client": client, "digest": state["digest"],
                                   "service": state["service_name"], "targets": state["targets"],
                                   "executable": executable, "binary_hash": binary_hash, "created": time.monotonic()}
        result.update(can_apply=True, plan_id=plan_id)
        return result

    def apply(self, plan_id: str) -> dict:
        if not self.use_environment:
            raise ValueError("隔离测试模式禁止修改实际 MAGPIE。")
        if not isinstance(plan_id, str):
            raise ValueError("预览编号无效，请重新扫描。")
        with self.lock:
            plan = self.plans.pop(plan_id, None)
            if not plan or time.monotonic() - plan["created"] > 600:
                raise ValueError("预览已过期或已使用，请重新扫描。")
            state = magpie_state(self.home, plan["client"], use_environment=True)
            if state["error"] or state["digest"] != plan["digest"] or state["route"] != "shared":
                raise ValueError("MAGPIE 配置在预览后发生变化，请重新扫描；没有执行切换。")
            validate_bundled_mcp(self.root)
            try:
                if file_digest(plan["executable"]) != plan["binary_hash"]:
                    raise ValueError("MAGPIE 程序在预览后发生变化，请重新扫描。")
                result = self.run([str(plan["executable"]), "library", "mcp", "router", plan["service"], "direct"],
                                  capture_output=True, timeout=45, check=False, stdin=subprocess.DEVNULL,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError("MAGPIE 操作未确认完成，可能已部分同步；请先检查 MAGPIE，勿重复操作。") from error
            after = magpie_state(self.home, plan["client"], use_environment=True)
            if (result.returncode or after["error"] or not after["managed"] or not after["hub_enabled"] or
                    after["policy"] != "direct" or after["service_name"] != plan["service"] or
                    after["targets"] != plan["targets"] or after["command"] != state["command"]):
                raise ValueError("MAGPIE 未确认完成切换，可能已部分同步；请先检查 MAGPIE，勿重复操作。")
            return {"route": "direct", "targets": plan["targets"],
                    "note": "MAGPIE 已保存直连设置。请重连各客户端并实测气泡来源；同步问题请在 MAGPIE 中核对。"}
