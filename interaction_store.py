"""Optional local care state. Preview playback never writes to this store."""
from __future__ import annotations

import json
import math
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from notification_store import default_database_path


DEFAULTS = {
    "enabled": False, "touch_enabled": True, "effects_enabled": True,
    "satiety": 80.0, "hydration": 80.0, "mood": 80.0,
    "updated_at": 0.0, "last_feed": 0.0, "last_drink": 0.0,
    "action_revision": 0, "last_action": "",
}
SWITCHES = {"enabled", "touch_enabled", "effects_enabled"}
COOLDOWN = 30
ACTION_TTL = 30


class InteractionStore:
    def __init__(self, database: Path | None = None):
        self.database = database or default_database_path()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS pet_care (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=2)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _load(connection, now):
        row = connection.execute("SELECT value FROM pet_care WHERE id=1").fetchone()
        care = {**DEFAULTS, **(json.loads(row[0]) if row else {})}
        previous = care["updated_at"] or now
        elapsed = max(0.0, min(8 * 3600, now - previous))
        if care["enabled"]:
            for key, rate in (("satiety", 3), ("hydration", 4), ("mood", 1.5)):
                care[key] = max(0.0, care[key] - rate * elapsed / 3600)
        # A clock adjustment must not make the same elapsed time decay twice.
        care["updated_at"] = max(now, previous)
        return care

    @staticmethod
    def _save(connection, care):
        connection.execute("INSERT OR REPLACE INTO pet_care VALUES (1, ?)",
                           (json.dumps(care),))

    @staticmethod
    def _public(care, now):
        return {**{key: value for key, value in care.items() if not key.startswith("_")},
                "feed_wait": max(0, math.ceil(care["last_feed"] + COOLDOWN - now)),
                "drink_wait": max(0, math.ceil(care["last_drink"] + COOLDOWN - now))}

    def snapshot(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            care = self._load(connection, now)
            self._save(connection, care)
        return self._public(care, now)

    def configure(self, patch: dict, now: float | None = None) -> dict:
        if not patch or set(patch) - SWITCHES or any(type(value) is not bool for value in patch.values()):
            raise ValueError("互动设置只接受养成、触摸与特效的开关。")
        now = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            care = self._load(connection, now)
            care.update(patch)
            if patch.get("enabled") is False:
                care["_desktop_actions"] = []
            self._save(connection, care)
        return self._public(care, now)

    def feed(self, action: str, now: float | None = None) -> dict:
        if action not in ("feed", "drink"):
            raise ValueError("请选择点心或喝水；其他动作只在试映室预览。")
        now = time.time() if now is None else now
        last_key = "last_" + action
        value_key = "satiety" if action == "feed" else "hydration"
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            care = self._load(connection, now)
            if not care["enabled"]:
                raise ValueError("请先开启并保存养成设置，或使用下方不改数值的动作预览。")
            if now < care[last_key] + COOLDOWN:
                raise ValueError("还在慢慢享用，请等冷却结束再来。")
            care[value_key] = min(100.0, care[value_key] + 20)
            care["mood"] = min(100.0, care["mood"] + 4)
            care[last_key] = now
            care["last_action"] = action
            care["action_revision"] = int(care.get("action_revision", 0)) + 1
            events = [event for event in care.get("_desktop_actions", [])
                      if 0 <= now - event["created_at"] < ACTION_TTL]
            events.append({"action": action, "revision": care["action_revision"], "created_at": now})
            care["_desktop_actions"] = events[-8:]
            self._save(connection, care)
        return {"status": "applied", "action": action, "care": self._public(care, now)}

    def take_action(self, now: float | None = None) -> dict | None:
        """Claim one recent cosmetic response; a click never depends on playback."""
        now = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            care = self._load(connection, now)
            events = [event for event in care.get("_desktop_actions", [])
                      if care["enabled"] and 0 <= now - event["created_at"] < ACTION_TTL]
            event = events.pop(0) if events else None
            care["_desktop_actions"] = events
            self._save(connection, care)
        return event
