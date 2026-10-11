"""Local, cross-process notification queue for the desktop pet and MCP host."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


def default_database_path() -> Path:
    override = os.environ.get("NIJIKA_PET_DB_PATH")
    if override:
        return Path(override).expanduser()
    # MSIX hosts can redirect AppData into a package-private cache. A user-owned
    # folder outside AppData gives Explorer, Codex and DSH the same physical file.
    return Path.home() / ".nijika-desktop-pet" / "notifications.sqlite3"


def _required_text(value: str, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    clean = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean or len(clean) > maximum or any(ord(char) < 32 and char != "\n" for char in clean):
        raise ValueError(f"{label} must contain 1–{maximum} printable characters")
    return clean


def _choice_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in value)


@dataclass(frozen=True)
class Notification:
    id: str
    agent: str
    title: str
    message: str
    choices: tuple[str, ...]
    choice_descriptions: tuple[str, ...]
    choice_recommended: tuple[bool, ...]
    status: str
    selected_index: int | None
    created_at: int
    updated_at: int
    kind: str = "agent"

    def result(self) -> dict[str, str | int | None]:
        choice = self.choices[self.selected_index] if self.selected_index is not None else None
        description = (self.choice_descriptions[self.selected_index]
                       if self.selected_index is not None else None)
        return {"request_id": self.id, "status": self.status, "choice": choice,
                "choice_description": description, "choice_index": self.selected_index}


class NotificationStore:
    def __init__(self, path: Path | None = None):
        self.path = path or default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    choices TEXT NOT NULL,
                    status TEXT NOT NULL,
                    selected_index INTEGER,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS notifications_pending
                ON notifications(status, created_at, id)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS notice_tags (
                    notification_id TEXT PRIMARY KEY,
                    event_key TEXT UNIQUE,
                    kind TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0
                )
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=1.0)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> Notification | None:
        if row is None:
            return None
        stored_choices = json.loads(row["choices"])
        labels = tuple(item if isinstance(item, str) else item["label"]
                       for item in stored_choices)
        descriptions = tuple("" if isinstance(item, str) else item["description"]
                             for item in stored_choices)
        return Notification(
            id=row["id"], agent=row["agent"], title=row["title"],
            message=row["message"], choices=labels,
            choice_descriptions=descriptions,
            choice_recommended=tuple(False if isinstance(item, str) else
                                     item.get("recommended", False)
                                     for item in stored_choices),
            status=row["status"], selected_index=row["selected_index"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            kind=row["kind"] if "kind" in row.keys() else "agent",
        )

    def create(self, agent: str, title: str, message: str,
               choices: tuple[str | dict[str, str], ...] | list[str | dict[str, str]],
               *, event_key: str | None = None, kind: str = "agent") -> Notification:
        agent = _required_text(agent, "agent", 20)
        title = _required_text(title, "title", 30)
        message = _required_text(message, "message", 120)
        if not isinstance(choices, (tuple, list)) or not 1 <= len(choices) <= 3:
            raise ValueError("choices must contain 1–3 labels")
        normalized: list[dict[str, str]] = []
        for item in choices:
            if isinstance(item, str):
                label, description = _required_text(item, "choice", 20), ""
            elif isinstance(item, dict):
                label = _required_text(item.get("label"), "choice label", 20)
                description = _required_text(item.get("description"), "choice description", 48)
                recommended = item.get("recommended", False)
                if not isinstance(recommended, bool):
                    raise ValueError("recommended must be true or false")
                if len(description) < 6 or description == label or "\n" in description:
                    raise ValueError("each choice needs a distinct one-line description of at least 6 characters")
            else:
                raise ValueError("each choice must be a label or label/description object")
            normalized.append({"label": label, "description": description,
                               "recommended": recommended if isinstance(item, dict) else False})
        if sum(item["recommended"] for item in normalized) > 1:
            raise ValueError("at most one choice may be recommended")
        if any("\n" in item["label"] or _choice_width(item["label"]) > 20
               for item in normalized):
            raise ValueError("choice labels must fit within 20 display columns")
        if len({item["label"] for item in normalized}) != len(normalized):
            raise ValueError("choice labels must be distinct")
        now = int(time.time())
        notice_id = uuid.uuid4().hex
        with self._connect() as connection:
            # Serialize deduplication with insertion across hook processes.
            connection.execute("BEGIN IMMEDIATE")
            if event_key:
                existing = connection.execute(
                    "SELECT notification_id FROM notice_tags WHERE event_key=?", (event_key,)
                ).fetchone()
                if existing:
                    notice_id = existing[0]
                    return self.get(notice_id)
            connection.execute(
                "INSERT INTO notifications VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                (notice_id, agent, title, message, json.dumps(normalized, ensure_ascii=False), now, now),
            )
            connection.execute(
                "INSERT INTO notice_tags VALUES (?, ?, ?, ?)",
                (notice_id, event_key, kind, 100 if kind == "approval" else 0),
            )
        return self.get(notice_id)

    def get(self, notice_id: str) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT n.*, COALESCE(t.kind, 'agent') AS kind FROM notifications n "
                "LEFT JOIN notice_tags t ON t.notification_id=n.id WHERE n.id = ?", (notice_id,)
            ).fetchone()
        return self._decode(row)

    def next_pending(self) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT n.*, COALESCE(t.kind, 'agent') AS kind FROM notifications n "
                "LEFT JOIN notice_tags t ON t.notification_id=n.id WHERE n.status = 'pending' "
                "ORDER BY COALESCE(t.priority, 0) DESC, n.created_at, n.rowid LIMIT 1"
            ).fetchone()
        return self._decode(row)

    def answer(self, notice_id: str, selected_index: int) -> Notification | None:
        if not isinstance(selected_index, int) or isinstance(selected_index, bool):
            raise ValueError("selected_index must be an integer")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM notifications WHERE id = ?", (notice_id,)
            ).fetchone()
            notice = self._decode(row)
            if notice is None:
                return None
            if notice.status == "pending":
                if not 0 <= selected_index < len(notice.choices):
                    raise ValueError("selected_index is outside available choices")
                connection.execute(
                    "UPDATE notifications SET status='answered', selected_index=?, updated_at=? "
                    "WHERE id=? AND status='pending'",
                    (selected_index, int(time.time()), notice_id),
                )
        return self.get(notice_id)

    def resolve_approval(self, event_key: str) -> None:
        """Tool completion clears the reminder without fabricating a user click."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE notifications SET status='resolved', updated_at=? "
                "WHERE status='pending' AND id IN "
                "(SELECT notification_id FROM notice_tags WHERE kind='approval' AND event_key=?)",
                (int(time.time()), event_key),
            )

    def dismiss(self, notice_id: str) -> Notification | None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE notifications SET status='dismissed', updated_at=? "
                "WHERE id=? AND status='pending'",
                (int(time.time()), notice_id),
            )
        return self.get(notice_id)

    def prune(self) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                "UPDATE notifications SET status='expired', updated_at=? "
                "WHERE status='pending' AND created_at < ?",
                (now, now - 30 * 86400),
            )
            connection.execute(
                "DELETE FROM notifications WHERE status != 'pending' AND updated_at < ?",
                (now - 7 * 86400,),
            )
            connection.execute(
                "DELETE FROM notice_tags WHERE notification_id NOT IN (SELECT id FROM notifications)"
            )
