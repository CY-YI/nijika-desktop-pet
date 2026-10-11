"""Keep already-running legacy MCP hosts usable during the queue-path upgrade."""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from notification_store import NotificationStore


def legacy_database_paths() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    candidates = [local / "NijikaDesktopPet" / "notifications.sqlite3"]
    packages = Path.home() / "AppData" / "Local" / "Packages"
    candidates.extend(packages.glob("OpenAI.Codex_*/LocalCache/Local/NijikaDesktopPet/notifications.sqlite3"))
    # resolve() also exposes MSIX redirection; never open the same file twice.
    return list(dict.fromkeys(p.resolve() for p in candidates if p.is_file()))


class LegacyQueueBridge:
    def __init__(self, store: NotificationStore, sources: list[Path]):
        self.store = store
        self.sources = [p for p in sources if p.resolve() != store.path.resolve()]
        with store._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS legacy_origins (
                    notification_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    PRIMARY KEY(notification_id, source_path)
                )
            """)

    def sync(self) -> list[str]:
        errors = []
        for path in self.sources:
            if not path.is_file():
                continue
            try:
                self._sync_source(path)
            except (OSError, sqlite3.Error) as error:
                errors.append(f"{path}: {type(error).__name__}")
        return errors

    def _sync_source(self, path: Path) -> None:
        with closing(sqlite3.connect(path, timeout=0.15)) as legacy, legacy:
            rows = legacy.execute(
                "SELECT id,agent,title,message,choices,status,selected_index,created_at,updated_at "
                "FROM notifications WHERE status='pending' AND created_at>=?",
                (int(time.time()) - 30 * 86400,),
            ).fetchall()
            with self.store._connect() as current:
                for row in rows:
                    current.execute("INSERT OR IGNORE INTO notifications VALUES (?,?,?,?,?,?,?,?,?)", row)
                    current.execute("INSERT OR IGNORE INTO legacy_origins VALUES (?,?)", (row[0], str(path)))
                replies = current.execute(
                    "SELECT n.id,n.status,n.selected_index,n.updated_at FROM notifications n "
                    "JOIN legacy_origins o ON n.id=o.notification_id "
                    "WHERE o.source_path=? AND n.status!='pending'", (str(path),)
                ).fetchall()
                for row in replies:
                    legacy.execute(
                        "UPDATE notifications SET status=?,selected_index=?,updated_at=? "
                        "WHERE id=? AND status='pending'", (row[1],row[2],row[3],row[0]),
                    )
                # An old renderer or client may have already handled a copied request.
                pending = current.execute(
                    "SELECT n.id FROM notifications n JOIN legacy_origins o ON n.id=o.notification_id "
                    "WHERE o.source_path=? AND n.status='pending'", (str(path),)
                ).fetchall()
                for row in pending:
                    reply = legacy.execute(
                        "SELECT status,selected_index,updated_at FROM notifications WHERE id=? AND status!='pending'",
                        (row[0],),
                    ).fetchone()
                    if reply:
                        current.execute(
                            "UPDATE notifications SET status=?,selected_index=?,updated_at=? WHERE id=? AND status='pending'",
                            (*reply, row[0]),
                        )
                current.execute("DELETE FROM legacy_origins WHERE notification_id NOT IN (SELECT id FROM notifications)")
