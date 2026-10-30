"""Local onboarding evidence, separate from notification payloads and permissions."""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path


class AgentActivity:
    def __init__(self, database: Path):
        self.database = database
        with closing(sqlite3.connect(database, timeout=1)) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS agent_activity (
                profile_id TEXT PRIMARY KEY, notification_id TEXT NOT NULL)""")

    def record(self, profile_id: str, notification_id: str) -> None:
        if not isinstance(profile_id, str) or not re.fullmatch("[0-9a-f]{32}", profile_id):
            return
        with closing(sqlite3.connect(self.database, timeout=1)) as connection, connection:
            connection.execute("INSERT OR REPLACE INTO agent_activity VALUES (?, ?)",
                               (profile_id, notification_id))

    def snapshot(self, profile_id: str) -> dict:
        with closing(sqlite3.connect(self.database, timeout=1)) as connection:
            row = connection.execute("""
                SELECT n.id, n.agent, s.software, n.status, n.created_at
                FROM agent_activity a JOIN notifications n ON n.id=a.notification_id
                LEFT JOIN notice_sources s ON s.notification_id=n.id
                WHERE a.profile_id=?""", (profile_id,)).fetchone()
        if not row:
            return {"called": False, "answered": False}
        return {"called": True, "answered": row[3] == "answered", "request_id": row[0],
                "agent": row[1], "software": row[2] or "", "status": row[3], "at": row[4]}
