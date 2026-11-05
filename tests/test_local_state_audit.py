import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from control_store import ControlStore
from tools.audit_local_state import audit


def png() -> bytes:
    image = Image.new("RGBA", (64, 96))
    ImageDraw.Draw(image).ellipse((16, 20, 48, 80), fill="gold")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class LocalStateAuditTests(unittest.TestCase):
    def test_read_only_audit_reports_duplicate_complete_agent_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state/notifications.sqlite3"
            store = ControlStore(database)
            skin = store.import_skin(png(), "portable skin.png")
            store.update_settings({"skin": skin["id"]})
            store.save_agent({
                "id": "one",
                "client": "custom",
                "location": str(Path(directory) / "project"),
                "agent_identity": "Codex",
                "software": "VS Code",
            })
            store.save_agent({
                "id": "two",
                "client": "custom",
                "location": str(Path(directory) / "project"),
                "agent_identity": "Codex",
                "software": "VS Code",
            })

            report = audit(database)

            self.assertEqual(report["status"], "conflict")
            self.assertTrue(report["selected_skin_present"])
            self.assertEqual(report["skin_count_including_default"], 2)
            self.assertEqual(report["duplicate_complete_agent_keys"][0]["count"], 2)

    def test_missing_database_is_reported_without_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing.sqlite3"

            report = audit(database)

            self.assertEqual(report["status"], "missing")
            self.assertFalse(database.exists())

    def test_malformed_settings_are_a_conflict_instead_of_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "broken.sqlite3"
            connection = sqlite3.connect(database)
            try:
                with connection:
                    connection.execute(
                        "CREATE TABLE panel_preferences (name TEXT PRIMARY KEY, value TEXT NOT NULL)"
                    )
                    connection.execute(
                        "CREATE TABLE panel_agents (id TEXT PRIMARY KEY, value TEXT NOT NULL)"
                    )
                    connection.execute(
                        "INSERT INTO panel_preferences VALUES ('settings', ?)",
                        ("{broken",),
                    )
            finally:
                connection.close()

            report = audit(database)

            self.assertEqual(report["status"], "conflict")
            self.assertFalse(report["settings_valid"])
            self.assertEqual(report["issues"][0]["kind"], "invalid_local_state")


if __name__ == "__main__":
    unittest.main()
