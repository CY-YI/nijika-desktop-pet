"""Local, cross-process notification queue for the desktop pet and MCP host."""

from __future__ import annotations

import hashlib
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
    software: str = ""

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
            connection.execute("""
                CREATE TABLE IF NOT EXISTS notice_sources (
                    notification_id TEXT PRIMARY KEY,
                    software TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS codex_turn_state (
                    session_hash TEXT NOT NULL,
                    turn_hash TEXT NOT NULL,
                    has_user_prompt INTEGER NOT NULL DEFAULT 0,
                    user_prompt_class TEXT NOT NULL DEFAULT 'unknown',
                    substantive_tool_count INTEGER NOT NULL DEFAULT 0,
                    nijika_notice_sent INTEGER NOT NULL DEFAULT 0,
                    completion_notice_sent INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (session_hash, turn_hash)
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
            software=row["software"] if "software" in row.keys() else "",
        )

    def create(self, agent: str, title: str, message: str,
               choices: tuple[str | dict[str, str], ...] | list[str | dict[str, str]],
               *, event_key: str | None = None, kind: str = "agent",
               software: str = "") -> Notification:
        agent = _required_text(agent, "agent", 20)
        title = _required_text(title, "title", 30)
        message = _required_text(message, "message", 120)
        if software:
            software = _required_text(software, "software", 40)
            if "\n" in software:
                raise ValueError("software must be one line")
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
                    "SELECT t.notification_id, n.status FROM notice_tags t "
                    "JOIN notifications n ON n.id = t.notification_id WHERE t.event_key=?",
                    (event_key,),
                ).fetchone()
                if existing and existing[1] == "pending":
                    return self.get(existing[0])
                if existing:
                    # A finished notice must not swallow a later request for the same
                    # event: clients without a turn id repeat commands within a session.
                    connection.execute("DELETE FROM notice_tags WHERE event_key=?", (event_key,))
            connection.execute(
                "INSERT INTO notifications VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                (notice_id, agent, title, message, json.dumps(normalized, ensure_ascii=False), now, now),
            )
            connection.execute(
                "INSERT INTO notice_tags VALUES (?, ?, ?, ?)",
                (notice_id, event_key, kind, 100 if kind == "approval" else 0),
            )
            connection.execute("INSERT INTO notice_sources VALUES (?, ?)", (notice_id, software))
        return self.get(notice_id)

    def get(self, notice_id: str) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT n.*, COALESCE(t.kind, 'agent') AS kind, COALESCE(s.software, '') AS software FROM notifications n "
                "LEFT JOIN notice_sources s ON s.notification_id=n.id "
                "LEFT JOIN notice_tags t ON t.notification_id=n.id WHERE n.id = ?", (notice_id,)
            ).fetchone()
        return self._decode(row)

    def next_pending(self) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT n.*, COALESCE(t.kind, 'agent') AS kind, COALESCE(s.software, '') AS software FROM notifications n "
                "LEFT JOIN notice_sources s ON s.notification_id=n.id "
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
            connection.execute(
                "DELETE FROM codex_turn_state WHERE completion_notice_sent=0 "
                "AND nijika_notice_sent=0 AND updated_at < ?",
                (now - 30 * 86400,),
            )

    @staticmethod
    def _turn_identity(session_id: object, turn_id: object) -> tuple[str, str]:
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 512:
            raise ValueError("session_id must be non-empty text")
        if not isinstance(turn_id, str) or not turn_id.strip() or len(turn_id) > 512:
            raise ValueError("turn_id must be non-empty text")
        # Hook payloads can contain private prompts and commands. Persist only
        # bounded opaque identities so repeated lifecycle events can be joined.
        session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        turn_hash = hashlib.sha256(turn_id.encode("utf-8")).hexdigest()
        return session_hash, turn_hash

    def begin_codex_turn(self, session_id: str, turn_id: str,
                         prompt_class: str) -> None:
        session_hash, turn_hash = self._turn_identity(session_id, turn_id)
        if prompt_class not in {"question", "substantive", "unknown", "internal"}:
            raise ValueError("invalid prompt class")
        now = int(time.time())
        with self._connect() as connection:
            # Hooks may be upgraded before the long-running pet binary. Prune
            # inactive state here too, rather than depending on its prune loop.
            connection.execute(
                "DELETE FROM codex_turn_state WHERE completion_notice_sent=0 "
                "AND nijika_notice_sent=0 AND updated_at < ?",
                (now - 30 * 86400,),
            )
            connection.execute(
                "INSERT INTO codex_turn_state "
                "(session_hash, turn_hash, has_user_prompt, user_prompt_class, "
                "substantive_tool_count, nijika_notice_sent, completion_notice_sent, "
                "created_at, updated_at) VALUES (?, ?, 1, ?, 0, 0, 0, ?, ?) "
                "ON CONFLICT(session_hash, turn_hash) DO UPDATE SET "
                "has_user_prompt=1, user_prompt_class=CASE "
                "WHEN user_prompt_class='internal' OR excluded.user_prompt_class='internal' "
                "THEN 'internal' ELSE excluded.user_prompt_class END, "
                "updated_at=excluded.updated_at",
                (session_hash, turn_hash, prompt_class, now, now),
            )

    def record_codex_tool(self, session_id: str, turn_id: str,
                          *, substantive: bool, notice_sent: bool) -> None:
        session_hash, turn_hash = self._turn_identity(session_id, turn_id)
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                "UPDATE codex_turn_state SET "
                "substantive_tool_count=substantive_tool_count+?, "
                "nijika_notice_sent=MAX(nijika_notice_sent, ?), "
                "updated_at=? WHERE session_hash=? AND turn_hash=?",
                (1 if substantive else 0, 1 if notice_sent else 0,
                 now, session_hash, turn_hash),
            )

    def create_codex_completion_notice(self, session_id: str,
                                       turn_id: str,
                                       *, result_class: str,
                                       message_preview: str | None = None) -> Notification | None:
        """Atomically create at most one safe completion notice for a turn."""
        if result_class not in {"empty", "brief", "deliverable", "waiting"}:
            raise ValueError("invalid result class")
        message = ("已完成本轮任务，请查看结果。" if message_preview is None else
                   _required_text(message_preview, "message_preview", 120))
        session_hash, turn_hash = self._turn_identity(session_id, turn_id)
        now = int(time.time())
        notice_id = uuid.uuid4().hex
        choices = json.dumps([{
            "label": "知道了", "description": "", "recommended": False,
        }], ensure_ascii=False)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT has_user_prompt, user_prompt_class, substantive_tool_count, "
                "nijika_notice_sent, completion_notice_sent "
                "FROM codex_turn_state WHERE session_hash=? AND turn_hash=?",
                (session_hash, turn_hash),
            ).fetchone()
            if (row is None or not row["has_user_prompt"]
                    or row["user_prompt_class"] == "internal"
                    or result_class == "empty"
                    or row["nijika_notice_sent"]
                    or row["completion_notice_sent"]):
                return None
            connection.execute(
                "INSERT INTO notifications VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                (notice_id, "ChatGPT", "任务完成", message,
                 choices, now, now),
            )
            connection.execute("INSERT INTO notice_sources VALUES (?, ?)", (notice_id, "Codex"))
            connection.execute(
                "UPDATE codex_turn_state SET completion_notice_sent=1, updated_at=? "
                "WHERE session_hash=? AND turn_hash=?",
                (now, session_hash, turn_hash),
            )
        return self.get(notice_id)
