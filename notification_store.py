"""Local, cross-process notification queue for the desktop pet and MCP host."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


TEXT_REPLY_LIMIT = 500
LEGACY_TEXT_REPLY_DESCRIPTION = "虹夏文字回复"
_NOTICE_QUERY = (
    "SELECT n.*, COALESCE(t.kind, 'agent') AS kind, COALESCE(s.software, '') AS software, "
    "(t.kind = 'agent' AND t.event_key IS NULL AND s.notification_id IS NOT NULL) AS agent_notice, "
    "r.notification_id AS text_request, r.reply_text, "
    "CASE WHEN h.client_id='codex' AND h.session_hash IS NOT NULL THEN 'codex' "
    "WHEN h.notification_id IS NOT NULL THEN 'reference' ELSE '' END AS reply_delivery FROM notifications n "
    "LEFT JOIN notice_sources s ON s.notification_id=n.id "
    "LEFT JOIN notice_tags t ON t.notification_id=n.id "
    "LEFT JOIN notice_text_replies r ON r.notification_id=n.id "
    "LEFT JOIN notice_host_reply_targets h ON h.notification_id=n.id "
)


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


def _is_agent_prompt(labels: tuple[str, ...], descriptions: tuple[str, ...]) -> bool:
    return ((labels == ("知道了",) and descriptions == ("",))
            or (2 <= len(labels) <= 3 and all(descriptions)))


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
    accepts_text: bool = False
    reply_text: str | None = None
    reply_delivery: str = ""

    def result(self) -> dict[str, str | int | None]:
        choice = self.choices[self.selected_index] if self.selected_index is not None else None
        description = (self.choice_descriptions[self.selected_index]
                       if self.selected_index is not None else None)
        result = {"request_id": self.id, "status": self.status, "choice": choice,
                  "choice_description": description, "choice_index": self.selected_index}
        if self.accepts_text:
            result["reply_text"] = self.reply_text
        return result


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
                CREATE TABLE IF NOT EXISTS notice_text_replies (
                    notification_id TEXT PRIMARY KEY,
                    reply_text TEXT
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS notice_host_reply_targets (
                    notification_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    session_hash TEXT,
                    origin_turn_hash TEXT,
                    announced_at INTEGER
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS notice_host_reply_session
                ON notice_host_reply_targets(session_hash, announced_at)
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
        # Old MCP writers tag completion and decision requests. Host fallback
        # completions are untagged; approvals use a separate kind.
        legacy_prompt = ("agent_notice" in row.keys() and row["agent_notice"]
                         and _is_agent_prompt(labels, descriptions))
        reply_text = row["reply_text"] if "reply_text" in row.keys() else None
        return Notification(
            id=row["id"], agent=row["agent"], title=row["title"],
            message=row["message"], choices=labels,
            choice_descriptions=descriptions,
            choice_recommended=tuple(False if isinstance(item, str) else
                                     item.get("recommended", False)
                                     for item in stored_choices),
            status=row["status"], selected_index=row["selected_index"] if reply_text is None else None,
            created_at=row["created_at"], updated_at=row["updated_at"],
            kind=row["kind"] if "kind" in row.keys() else "agent",
            software=row["software"] if "software" in row.keys() else "",
            accepts_text=bool(legacy_prompt or ("text_request" in row.keys() and row["text_request"] is not None)),
            reply_text=reply_text,
            reply_delivery=row["reply_delivery"] if "reply_delivery" in row.keys() else "",
        )

    def create(self, agent: str, title: str, message: str,
               choices: tuple[str | dict[str, str], ...] | list[str | dict[str, str]],
               *, event_key: str | None = None, kind: str = "agent",
               software: str = "", accepts_text: bool = False,
               approval_target: tuple[str, object, object] | None = None) -> Notification | None:
        agent = _required_text(agent, "agent", 20)
        title = _required_text(title, "title", 30)
        message = _required_text(message, "message", 120)
        if software:
            software = _required_text(software, "software", 40)
            if "\n" in software:
                raise ValueError("software must be one line")
        if not isinstance(choices, (tuple, list)) or len(choices) > 3 or (not choices and not accepts_text):
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
        if accepts_text:
            agent_prompt = kind == "agent" and event_key is None
            local_demo = kind == "text_demo" and event_key in ("text-reply-demo", "completion-demo", "decision-demo")
            if not (agent_prompt or local_demo) or (normalized and not _is_agent_prompt(
                tuple(item["label"] for item in normalized), tuple(item["description"] for item in normalized)
            )):
                raise ValueError("text replies require an agent question, decision, or completion")
        if approval_target is not None and (kind != "approval" or not event_key):
            raise ValueError("native approval replies require an approval event")
        now = int(time.time())
        notice_id = uuid.uuid4().hex
        with self._connect() as connection:
            # Serialize deduplication with insertion across hook processes.
            connection.execute("BEGIN IMMEDIATE")
            if approval_target is not None:
                client, session, turn = approval_target
                try:
                    session_hash, turn_hash = self._turn_identity(session, turn, client)
                except ValueError:
                    session_hash = turn_hash = None
                if client == "codex" and connection.execute(
                    "SELECT 1 FROM codex_turn_state WHERE session_hash=? AND turn_hash=? "
                    "AND has_user_prompt=1 AND user_prompt_class!='internal' "
                    "AND completion_notice_sent=0",
                    (session_hash, turn_hash),
                ).fetchone() is None:
                    return None
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
            if accepts_text:
                connection.execute("INSERT INTO notice_text_replies (notification_id) VALUES (?)", (notice_id,))
            if approval_target is not None:
                self._add_host_reply(connection, notice_id, client, session_hash, turn_hash)
        return self.get(notice_id)

    def create_text_demo(self) -> Notification:
        return self.create("虹夏", "体验文字回复", "写一句话试试。回复只保存在本机演示里。", (),
                           kind="text_demo", event_key="text-reply-demo", software="本机演示", accepts_text=True)

    def get(self, notice_id: str) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                _NOTICE_QUERY + "WHERE n.id = ?", (notice_id,)
            ).fetchone()
        return self._decode(row)

    def next_pending(self) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                _NOTICE_QUERY + "WHERE n.status = 'pending' "
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

    def answer_text(self, notice_id: str, text: str) -> bool:
        """Persist the first answer to this pending text request only."""
        reply = _required_text(text, "reply", TEXT_REPLY_LIMIT)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(_NOTICE_QUERY + "WHERE n.id = ?", (notice_id,)).fetchone()
            notice = self._decode(row)
            if notice is None or notice.status != "pending" or not notice.accepts_text:
                return False
            choices = row["choices"]
            selected_index = None
            if not row["text_request"] or notice.reply_delivery:
                # A process that was already running may still read the old
                # choice fields. Keep that reader on the original request ID.
                entries = json.loads(choices)
                selected_index = len(entries)
                entries.append({"label": reply, "description": LEGACY_TEXT_REPLY_DESCRIPTION})
                choices = json.dumps(entries, ensure_ascii=False)
            connection.execute(
                "UPDATE notifications SET status='answered', choices=?, selected_index=?, updated_at=? WHERE id=?",
                (choices, selected_index, int(time.time()), notice_id),
            )
            connection.execute(
                "INSERT INTO notice_text_replies VALUES (?, ?) "
                "ON CONFLICT(notification_id) DO UPDATE SET reply_text=excluded.reply_text",
                (notice_id, reply),
            )
        return True

    def resolve_approval(self, event_key: str) -> None:
        """Tool completion clears the reminder without fabricating a user click."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE notifications SET status='resolved', updated_at=? "
                "WHERE status='pending' AND id IN "
                "(SELECT notification_id FROM notice_tags WHERE kind='approval' AND event_key=?)",
                (int(time.time()), event_key),
            )

    @staticmethod
    def _add_host_reply(connection: sqlite3.Connection, notice_id: str, client_id: str,
                        session_hash: str | None, turn_hash: str | None) -> None:
        connection.execute("INSERT INTO notice_text_replies (notification_id) VALUES (?)", (notice_id,))
        connection.execute("INSERT INTO notice_host_reply_targets VALUES (?, ?, ?, ?, NULL)",
                           (notice_id, client_id, session_hash, turn_hash))

    def take_host_reply_ids(self, session_id: object, turn_id: object, *, client_id: str) -> list[str]:
        session_hash, turn_hash = self._turn_identity(session_id, turn_id, client_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT h.notification_id FROM notice_host_reply_targets h "
                "JOIN notifications n ON n.id=h.notification_id "
                "JOIN notice_text_replies r ON r.notification_id=h.notification_id "
                "WHERE h.client_id=? AND h.session_hash=? AND h.origin_turn_hash!=? "
                "AND h.announced_at IS NULL AND n.status='answered' AND r.reply_text IS NOT NULL "
                "ORDER BY n.updated_at, n.rowid LIMIT 5", (client_id, session_hash, turn_hash),
            ).fetchall()
            ids = [row[0] for row in rows if re.fullmatch(r"[a-f0-9]{32}", row[0])]
            connection.executemany("UPDATE notice_host_reply_targets SET announced_at=? WHERE notification_id=?",
                                   [(int(time.time()), rid) for rid in ids])
        return ids

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
                "DELETE FROM notice_text_replies WHERE notification_id NOT IN (SELECT id FROM notifications)"
            )
            connection.execute(
                "DELETE FROM notice_host_reply_targets WHERE notification_id NOT IN (SELECT id FROM notifications)"
            )
            connection.execute(
                "DELETE FROM codex_turn_state WHERE completion_notice_sent=0 "
                "AND nijika_notice_sent=0 AND updated_at < ?",
                (now - 30 * 86400,),
            )

    @staticmethod
    def _turn_identity(session_id: object, turn_id: object,
                       client_id: str = "codex") -> tuple[str, str]:
        if not isinstance(client_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", client_id):
            raise ValueError("client_id must be a bounded lowercase identifier")
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 512:
            raise ValueError("session_id must be non-empty text")
        if not isinstance(turn_id, str) or not turn_id.strip() or len(turn_id) > 512:
            raise ValueError("turn_id must be non-empty text")
        # Hook payloads can contain private prompts and commands. Persist only
        # bounded opaque identities so repeated lifecycle events can be joined.
        # Preserve old Codex tombstones. Namespace other clients so identical
        # session and turn IDs from different hosts never collide.
        session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        if client_id != "codex":
            session_hash = hashlib.sha256(client_id.encode("ascii")).hexdigest() + ":" + session_hash
        turn_hash = hashlib.sha256(turn_id.encode("utf-8")).hexdigest()
        return session_hash, turn_hash

    def begin_codex_turn(self, session_id: str, turn_id: str,
                         prompt_class: str) -> None:
        self.begin_turn(session_id, turn_id, prompt_class, client_id="codex")

    def begin_turn(self, session_id: str, turn_id: str, prompt_class: str,
                   *, client_id: str) -> None:
        session_hash, turn_hash = self._turn_identity(session_id, turn_id, client_id)
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
        self.record_turn_tool(session_id, turn_id, substantive=substantive,
                              notice_sent=notice_sent, client_id="codex")

    def record_turn_tool(self, session_id: str, turn_id: str,
                         *, substantive: bool, notice_sent: bool,
                         client_id: str) -> None:
        session_hash, turn_hash = self._turn_identity(session_id, turn_id, client_id)
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
        return self.create_completion_notice(
            session_id, turn_id, result_class=result_class,
            message_preview=message_preview, client_id="codex",
            agent="ChatGPT", software="Codex",
        )

    def create_completion_notice(self, session_id: str, turn_id: str, *,
                                 result_class: str, client_id: str,
                                 agent: str, software: str,
                                 message_preview: str | None = None) -> Notification | None:
        """Atomically create at most one safe completion notice for a turn."""
        agent = _required_text(agent, "agent", 20)
        software = _required_text(software, "software", 40)
        if "\n" in software:
            raise ValueError("software must be one line")
        if result_class not in {"empty", "brief", "deliverable", "waiting", "internal"}:
            raise ValueError("invalid result class")
        message = ("已完成本轮任务，请查看结果。" if message_preview is None else
                   _required_text(message_preview, "message_preview", 120))
        session_hash, turn_hash = self._turn_identity(session_id, turn_id, client_id)
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
            if row is None or not row["has_user_prompt"]:
                return None
            if client_id == "codex":
                connection.execute(
                    "UPDATE notifications SET status='resolved', updated_at=? "
                    "WHERE status='pending' AND id IN ("
                    "SELECT h.notification_id FROM notice_host_reply_targets h "
                    "JOIN notice_tags t ON t.notification_id=h.notification_id "
                    "WHERE h.client_id='codex' AND h.session_hash=? AND h.origin_turn_hash=? "
                    "AND t.kind='approval')",
                    (now, session_hash, turn_hash),
                )
            if row["completion_notice_sent"]:
                return None
            # A Stop consumes the completion slot even when another notice
            # already covered the turn or the output is internal.
            connection.execute(
                "UPDATE codex_turn_state SET completion_notice_sent=1, updated_at=? "
                "WHERE session_hash=? AND turn_hash=?",
                (now, session_hash, turn_hash),
            )
            if (row["nijika_notice_sent"] or row["user_prompt_class"] == "internal"
                    or result_class in {"empty", "internal"}):
                return None
            connection.execute(
                "INSERT INTO notifications VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                (notice_id, agent, "任务完成", message,
                 choices, now, now),
            )
            connection.execute("INSERT INTO notice_sources VALUES (?, ?)", (notice_id, software))
            self._add_host_reply(connection, notice_id, client_id, session_hash, turn_hash)
        return self.get(notice_id)
