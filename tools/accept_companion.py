"""Reusable acceptance check for the four phase-1 companion features.

Drives the running settings window over its loopback API, verifies the focus
timer, break reminders, daily notes and companionship counters, then restores
every setting it touched. Run the settings window first (``虹夏桌宠.exe
--control-panel``); by default it targets the pet's own panel-status file.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

STATUS_PATH = Path.home() / ".nijika-desktop-pet" / "panel-status.json"
NOTE_TEXT = "验收用临时便签（本脚本会自动删除）"


def token_for(base: str) -> str:
    with urllib.request.urlopen(base + "/", timeout=5) as response:
        page = response.read().decode("utf-8")
    match = re.search(r'<meta name="nijika-token" content="([^"]+)"', page)
    if not match:
        raise SystemExit("设置窗口没有返回会话令牌，请重新打开设置中心。")
    return match.group(1)


def call(base: str, token: str, route: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base + route, data=body, method="GET" if body is None else "POST")
    request.add_header("X-Nijika-Token", token)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return {"http_error": error.code, "body": error.read().decode("utf-8", "replace")}


def verify() -> list[str]:
    base = json.loads(STATUS_PATH.read_text(encoding="utf-8"))["url"]
    token = token_for(base)
    checks: list[str] = []
    before = call(base, token, "/api/state")["companion"]

    def expect(label: str, condition: bool) -> None:
        if not condition:
            raise SystemExit("验收失败：" + label)
        checks.append(label)

    started = call(base, token, "/api/focus", {"action": "start"})
    expect("专注开始后为运行状态", started.get("status") == "running" and started.get("mode") == "focus")
    expect("专注开始后剩余时间为设定时长", started.get("remaining_seconds") == started.get("focus_minutes") * 60)
    paused = call(base, token, "/api/focus", {"action": "pause"})
    expect("暂停后状态为 paused", paused.get("status") == "paused")
    resumed = call(base, token, "/api/focus", {"action": "resume"})
    expect("继续后恢复运行", resumed.get("status") == "running")
    reset = call(base, token, "/api/focus", {"action": "reset"})
    expect("结束后回到 idle", reset.get("status") == "idle")
    rejected = call(base, token, "/api/focus", {"action": "configure", "focus_minutes": 999})
    expect("非法时长被拒绝", "error" in rejected or "http_error" in rejected)

    reminders = before["reminders"]
    call(base, token, "/api/reminders", {"pause_minutes": 60})
    muted = call(base, token, "/api/state")["companion"]["reminders"]
    expect("免打扰写入未来的暂停时间", muted["paused_until"] > time.time())
    call(base, token, "/api/reminders", {"pause_minutes": 0})
    restored_pause = 0
    if reminders["paused_until"] > time.time():
        restored_pause = max(1, math.ceil((reminders["paused_until"] - time.time()) / 60))
    call(base, token, "/api/reminders", {"enabled": reminders["enabled"],
                                         "sedentary_minutes": reminders["sedentary_minutes"],
                                         "water_minutes": reminders["water_minutes"],
                                         "eye_minutes": reminders["eye_minutes"]})
    if restored_pause:
        call(base, token, "/api/reminders", {"pause_minutes": restored_pause})
    live = call(base, token, "/api/state")["companion"]["reminders"]
    expect("提醒间隔已还原", live["sedentary_minutes"] == reminders["sedentary_minutes"]
           and live["water_minutes"] == reminders["water_minutes"]
           and live["eye_minutes"] == reminders["eye_minutes"]
           and live["enabled"] == reminders["enabled"])

    points_before = before["affection"]["points"]
    note = call(base, token, "/api/notes", {"action": "add", "text": NOTE_TEXT})
    expect("便签创建成功", note.get("text") == NOTE_TEXT and note.get("done") is False)
    note_id = int(note["id"])
    expect("便签可以打勾", call(base, token, "/api/notes", {"action": "toggle", "id": note_id}).get("done") is True)
    after = call(base, token, "/api/state")["companion"]
    expect("打勾后好感度增加 2 点", after["affection"]["points"] == points_before + 2)
    expect("完成计数累加", after["affection"]["notes_done"] == before["affection"]["notes_done"] + 1)
    call(base, token, "/api/notes", {"action": "remove", "id": note_id})
    final = call(base, token, "/api/state")["companion"]
    expect("临时便签已清理", len(final["notes"]) == len(before["notes"]))
    expect("陪伴天数与阶段可读", final["affection"]["days"] >= 1 and bool(final["affection"]["stage"]["name"]))
    return checks


def main() -> int:
    for label in verify():
        print("通过：" + label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
