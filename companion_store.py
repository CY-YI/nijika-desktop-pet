"""Local focus timer, break reminders, daily notes and companionship data.

Everything lives in the same SQLite file as the notification queue so the pet,
the settings window and the MCP server all read one source of truth. All writes
stay on this computer.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from notification_store import default_database_path

POMODORO_DEFAULTS = {"focus_minutes": 25, "break_minutes": 5}
REMINDER_DEFAULTS = {
    "enabled": True,
    "sedentary_minutes": 50,
    "water_minutes": 45,
    "eye_minutes": 40,
}
KINDS = ("sedentary", "water", "eye")
STAGES = (
    (0, "初识", "刚认识，慢慢来就好。"),
    (30, "熟悉", "我们已经熟起来啦。"),
    (80, "亲近", "有你在的时候，工作也轻松一点。"),
    (160, "默契", "不用说话，也知道你在忙什么。"),
    (300, "挚友", "不管多晚，我都陪着你。"),
)
AFFECTION_PER_ACTION = {"pet": 1, "greet": 2, "focus": 5, "note": 2, "decision": 2}


def _today() -> str:
    return date.today().isoformat()


def stage_for(points: int) -> dict:
    index = 0
    for position, (threshold, _, _) in enumerate(STAGES):
        if points >= threshold:
            index = position
    name, line = STAGES[index][1], STAGES[index][2]
    nxt = STAGES[index + 1][0] if index + 1 < len(STAGES) else None
    return {"index": index, "name": name, "line": line, "next_at": nxt,
            "progress": 1.0 if nxt is None else max(0.0, min(1.0, (points - STAGES[index][0]) / (nxt - STAGES[index][0])))}


class CompanionStore:
    """Small, transactional store for the phase-1 companion features."""

    def __init__(self, database: Path | None = None):
        self.database = database or default_database_path()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = self.connect()
        try:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS companion_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS companion_notes ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, text TEXT NOT NULL, "
                    "done INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL)"
                )
        finally:
            connection.close()

    def connect(self):
        return sqlite3.connect(self.database, timeout=2)

    # ---------- generic helpers ----------

    def _document(self, connection, name: str, default: dict) -> dict:
        row = connection.execute("SELECT value FROM companion_state WHERE name=?", (name,)).fetchone()
        if not row:
            return dict(default)
        try:
            import json
            value = json.loads(row[0])
            return {**default, **value} if isinstance(value, dict) else dict(default)
        except ValueError:
            return dict(default)

    def _save(self, connection, name: str, value: dict) -> None:
        import json
        connection.execute("INSERT OR REPLACE INTO companion_state VALUES (?, ?)",
                           (name, json.dumps(value, ensure_ascii=False)))

    # ---------- pomodoro ----------

    def _pomodoro(self, connection) -> dict:
        default = {**POMODORO_DEFAULTS, "status": "idle", "mode": "focus", "ends_at": 0.0,
                   "remaining": POMODORO_DEFAULTS["focus_minutes"] * 60.0, "completed_today": 0,
                   "day": _today(), "focus_seconds_today": 0.0}
        state = self._document(connection, "pomodoro", default)
        if state.get("day") != _today():
            state["day"] = _today()
            state["completed_today"] = 0
            state["focus_seconds_today"] = 0.0
        return state

    def pomodoro(self) -> dict:
        connection = self.connect()
        try:
            state = self._pomodoro(connection)
            if state["status"] == "running" and state["ends_at"] <= time.time():
                state = self._advance(connection, state)
            return self._pomodoro_view(state)
        finally:
            connection.close()

    @staticmethod
    def _pomodoro_view(state: dict) -> dict:
        remaining = state["remaining"]
        phase = 0.0
        if state["status"] == "running":
            remaining = max(0.0, state["ends_at"] - time.time())
            total = (state["focus_minutes"] if state["mode"] == "focus" else state["break_minutes"]) * 60.0
            phase = 0.0 if total <= 0 else 1.0 - remaining / total
        return {**state, "remaining_seconds": int(round(remaining)),
                "phase": max(0.0, min(1.0, phase))}

    def _advance(self, connection, state: dict) -> dict:
        """Finish the current phase and move to the next one."""
        if state["mode"] == "focus":
            state["completed_today"] += 1
            state["focus_seconds_today"] += state["focus_minutes"] * 60.0
            state["mode"] = "break"
            seconds = state["break_minutes"] * 60.0
            self._record(connection, "focus", bonus=0)
            event = "focus_done"
        else:
            state["mode"] = "focus"
            seconds = state["focus_minutes"] * 60.0
            event = "break_done"
        state["status"] = "running"
        state["remaining"] = seconds
        state["ends_at"] = time.time() + seconds
        state["event"] = event
        state["event_at"] = time.time()
        self._save(connection, "pomodoro", state)
        connection.commit()
        return state

    def pomodoro_action(self, action: str, **values) -> dict:
        connection = self.connect()
        try:
            state = self._pomodoro(connection)
            if action == "start":
                state["mode"] = "focus"
                seconds = self._minutes(values, "focus_minutes", state) * 60.0
                state["status"] = "running"
                state["remaining"] = seconds
                state["ends_at"] = time.time() + seconds
            elif action == "pause":
                if state["status"] == "running":
                    state["remaining"] = max(0.0, state["ends_at"] - time.time())
                    state["status"] = "paused"
                    state["ends_at"] = 0.0
            elif action == "resume":
                if state["status"] == "paused":
                    state["status"] = "running"
                    state["ends_at"] = time.time() + state["remaining"]
            elif action == "reset":
                state.update({"status": "idle", "mode": "focus", "ends_at": 0.0,
                              "remaining": state["focus_minutes"] * 60.0})
            elif action == "skip":
                state = self._advance(connection, state)
                return self._pomodoro_view(self._pomodoro(connection))
            elif action == "configure":
                for key in ("focus_minutes", "break_minutes"):
                    if key in values:
                        minutes = values[key]
                        if type(minutes) is not int or not 1 <= minutes <= 180:
                            raise ValueError("专注与休息时长需要是 1–180 的整数分钟。")
                        state[key] = minutes
                if state["status"] == "idle":
                    state["remaining"] = state["focus_minutes"] * 60.0
            else:
                raise ValueError("不支持的专注计时操作。")
            self._save(connection, "pomodoro", state)
            connection.commit()
            return self._pomodoro_view(self._pomodoro(connection))
        finally:
            connection.close()

    @staticmethod
    def _minutes(values: dict, key: str, state: dict) -> int:
        minutes = values.get(key, state[key])
        if type(minutes) is not int or not 1 <= minutes <= 180:
            raise ValueError("专注与休息时长需要是 1–180 的整数分钟。")
        return minutes

    def take_event(self) -> str | None:
        """Return a pending phase-change event once, so the pet can announce it."""
        connection = self.connect()
        try:
            state = self._pomodoro(connection)
            if state["status"] == "running" and state["ends_at"] <= time.time():
                state = self._advance(connection, state)
            event = state.pop("event", None)
            if event:
                self._save(connection, "pomodoro", state)
                connection.commit()
            return event
        finally:
            connection.close()

    # ---------- break reminders ----------

    @staticmethod
    def _reminder_default(now: float) -> dict:
        state = {**REMINDER_DEFAULTS, "last": {kind: now for kind in KINDS}, "paused_until": 0.0}
        return state

    def _reminder_state(self, connection, now: float | None = None) -> dict:
        """Load reminders, starting each countdown the first time we see it."""
        now = time.time() if now is None else now
        state = self._document(connection, "reminders", self._reminder_default(now))
        last = state.get("last")
        if not isinstance(last, dict):
            last = {}
        changed = False
        for kind in KINDS:
            if not isinstance(last.get(kind), (int, float)):
                last[kind] = now
                changed = True
        state["last"] = last
        if changed:
            self._save(connection, "reminders", state)
            connection.commit()
        return state

    def reminders(self) -> dict:
        connection = self.connect()
        try:
            return self._reminder_state(connection)
        finally:
            connection.close()

    def update_reminders(self, patch: dict) -> dict:
        allowed = set(REMINDER_DEFAULTS)
        if not patch or set(patch) - allowed:
            raise ValueError("包含不支持的提醒设置。")
        connection = self.connect()
        try:
            state = self._reminder_state(connection)
            for key, value in patch.items():
                if key == "enabled":
                    if type(value) is not bool:
                        raise ValueError("提醒开关只能是开或关。")
                    state[key] = value
                else:
                    if type(value) is not int or not 5 <= value <= 240:
                        raise ValueError("提醒间隔需要是 5–240 的整数分钟。")
                    state[key] = value
            now = time.time()
            state["last"] = {kind: now for kind in KINDS}
            self._save(connection, "reminders", state)
            connection.commit()
            return state
        finally:
            connection.close()

    def due_reminder(self) -> str | None:
        """Return the reminder kind that is due now, if any."""
        connection = self.connect()
        try:
            state = self._reminder_state(connection)
            if not state.get("enabled", True) or time.time() < state.get("paused_until", 0.0):
                return None
            now = time.time()
            last = state.get("last", {})
            for kind in KINDS:
                minutes = state.get(f"{kind}_minutes", REMINDER_DEFAULTS[f"{kind}_minutes"])
                previous = float(last.get(kind, now))
                if now - previous >= minutes * 60.0:
                    last[kind] = now
                    state["last"] = last
                    self._save(connection, "reminders", state)
                    connection.commit()
                    return kind
            return None
        finally:
            connection.close()

    def pause_reminders(self, minutes: int) -> dict:
        if type(minutes) is not int or not 0 <= minutes <= 480:
            raise ValueError("免打扰时长需要是 0–480 分钟。")
        connection = self.connect()
        try:
            state = self._reminder_state(connection)
            state["paused_until"] = time.time() + minutes * 60.0 if minutes else 0.0
            self._save(connection, "reminders", state)
            connection.commit()
            return state
        finally:
            connection.close()

    # ---------- daily notes ----------

    def notes(self, day: str | None = None) -> list[dict]:
        day = day or _today()
        connection = self.connect()
        try:
            rows = connection.execute(
                "SELECT id, text, done, created_at FROM companion_notes WHERE day=? ORDER BY id", (day,)
            ).fetchall()
            return [{"id": row[0], "text": row[1], "done": bool(row[2]), "created_at": row[3]} for row in rows]
        finally:
            connection.close()

    def add_note(self, text: str, day: str | None = None) -> dict:
        text = (text or "").strip()
        if not text or len(text) > 120:
            raise ValueError("便签内容限 1–120 字。")
        day = day or _today()
        connection = self.connect()
        try:
            count = connection.execute("SELECT COUNT(*) FROM companion_notes WHERE day=?", (day,)).fetchone()[0]
            if count >= 20:
                raise ValueError("今天的便签最多 20 条。")
            with connection:
                cursor = connection.execute(
                    "INSERT INTO companion_notes (day, text, done, created_at) VALUES (?, ?, 0, ?)",
                    (day, text, time.time()))
                note_id = cursor.lastrowid
            return {"id": note_id, "text": text, "done": False}
        finally:
            connection.close()

    def toggle_note(self, note_id: int) -> dict:
        connection = self.connect()
        try:
            row = connection.execute("SELECT done FROM companion_notes WHERE id=?", (note_id,)).fetchone()
            if not row:
                raise ValueError("找不到这条便签。")
            done = 0 if row[0] else 1
            with connection:
                connection.execute("UPDATE companion_notes SET done=? WHERE id=?", (done, note_id))
            if done:
                self._record(connection, "note")
            return {"id": note_id, "done": bool(done)}
        finally:
            connection.close()

    def remove_note(self, note_id: int) -> None:
        connection = self.connect()
        try:
            with connection:
                connection.execute("DELETE FROM companion_notes WHERE id=?", (note_id,))
        finally:
            connection.close()

    def prune_notes(self, keep_days: int = 30) -> int:
        cutoff = (date.today() - timedelta(days=keep_days)).isoformat()
        connection = self.connect()
        try:
            with connection:
                cursor = connection.execute("DELETE FROM companion_notes WHERE day < ?", (cutoff,))
            return cursor.rowcount
        finally:
            connection.close()

    # ---------- affection ----------

    def _affection(self, connection) -> dict:
        default = {"first_seen": _today(), "points": 0, "interactions": 0, "last_seen": _today(),
                   "focus_total": 0, "notes_done": 0}
        state = self._document(connection, "affection", default)
        today = _today()
        if state.get("last_seen") != today:
            state["last_seen"] = today
            self._save(connection, "affection", state)
            connection.commit()
        return state

    def affection(self) -> dict:
        connection = self.connect()
        try:
            state = self._affection(connection)
            view = self._affection_view(state)
            return view
        finally:
            connection.close()

    @staticmethod
    def _affection_view(state: dict) -> dict:
        try:
            first = datetime.fromisoformat(state.get("first_seen", _today())).date()
        except ValueError:
            first = date.today()
        days = max(1, (date.today() - first).days + 1)
        stage = stage_for(int(state.get("points", 0)))
        return {**state, "days": days, "stage": stage}

    def record_interaction(self, kind: str, amount: int | None = None) -> dict:
        connection = self.connect()
        try:
            self._record(connection, kind, amount)
            return self._affection_view(self._affection(connection))
        finally:
            connection.close()

    def _record(self, connection, kind: str, amount: int | None = None, *, bonus: int = 0) -> None:
        state = self._affection(connection)
        gained = AFFECTION_PER_ACTION.get(kind, 0) if amount is None else max(0, amount)
        gained += bonus
        state["points"] = int(state.get("points", 0)) + gained
        state["interactions"] = int(state.get("interactions", 0)) + 1
        if kind == "focus":
            state["focus_total"] = int(state.get("focus_total", 0)) + 1
        if kind == "note":
            state["notes_done"] = int(state.get("notes_done", 0)) + 1
        self._save(connection, "affection", state)
        connection.commit()

    # ---------- aggregate ----------

    def snapshot(self) -> dict:
        return {"pomodoro": self.pomodoro(), "reminders": self.reminders(),
                "notes": self.notes(), "affection": self.affection()}
