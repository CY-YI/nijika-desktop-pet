"""Meaningful behaviour tests for focus timer, reminders, notes and affection."""
from __future__ import annotations

import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from companion_store import CompanionStore, stage_for


class PomodoroTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = CompanionStore(Path(self.temporary.name) / "state/notifications.sqlite3")

    def test_start_pause_resume_and_reset_keep_one_phase(self):
        started = self.store.pomodoro_action("start", focus_minutes=1, break_minutes=1)
        self.assertEqual(started["status"], "running")
        self.assertEqual(started["mode"], "focus")
        self.assertLessEqual(started["remaining_seconds"], 60)
        paused = self.store.pomodoro_action("pause")
        self.assertEqual(paused["status"], "paused")
        resumed = self.store.pomodoro_action("resume")
        self.assertEqual(resumed["status"], "running")
        reset = self.store.pomodoro_action("reset")
        self.assertEqual(reset["status"], "idle")
        self.assertEqual(reset["remaining_seconds"], reset["focus_minutes"] * 60)

    def test_finished_focus_records_points_and_switches_to_break_once(self):
        state = self.store.pomodoro_action("start", focus_minutes=1, break_minutes=1)
        connection = self.store.connect()
        try:
            with connection:
                connection.execute("UPDATE companion_state SET value=? WHERE name='pomodoro'",
                                   ('{"status":"running","mode":"focus","ends_at":1,"remaining":0,'
                                    '"focus_minutes":1,"break_minutes":1,"completed_today":0,'
                                    '"day":"' + date.today().isoformat() + '","focus_seconds_today":0}',))
        finally:
            connection.close()
        event = self.store.take_event()
        self.assertEqual(event, "focus_done")
        after = self.store.pomodoro()
        self.assertEqual(after["mode"], "break")
        self.assertEqual(after["completed_today"], 1)
        self.assertGreaterEqual(self.store.affection()["points"], 5)
        self.assertIsNone(self.store.take_event())

    def test_configure_rejects_out_of_range_minutes(self):
        for value in (0, 181, True, "25"):
            with self.assertRaises(ValueError):
                self.store.pomodoro_action("configure", focus_minutes=value)


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = CompanionStore(Path(self.temporary.name) / "state/notifications.sqlite3")

    def test_intervals_validate_and_due_order_is_stable(self):
        state = self.store.update_reminders({"sedentary_minutes": 60, "water_minutes": 30, "eye_minutes": 20})
        self.assertEqual(state["sedentary_minutes"], 60)
        for patch in ({"water_minutes": 4}, {"eye_minutes": 999}, {"enabled": "yes"}, {"unknown": 1}):
            with self.assertRaises(ValueError):
                self.store.update_reminders(patch)
        # A fresh install counts from now instead of interrupting immediately.
        self.assertIsNone(self.store.due_reminder())
        self._rewind(20 * 60)
        self.assertEqual(self.store.due_reminder(), "eye")
        self._rewind(10 * 60)
        self.assertEqual(self.store.due_reminder(), "water")
        self._rewind(30 * 60)
        self.assertEqual(self.store.due_reminder(), "sedentary")

    def _rewind(self, seconds: float) -> None:
        connection = self.store.connect()
        try:
            import json
            row = connection.execute("SELECT value FROM companion_state WHERE name='reminders'").fetchone()
            state = json.loads(row[0])
            state["last"] = {kind: value - seconds for kind, value in state["last"].items()}
            with connection:
                connection.execute("UPDATE companion_state SET value=? WHERE name='reminders'",
                                   (json.dumps(state),))
        finally:
            connection.close()

    def test_disabled_or_paused_reminders_stay_silent(self):
        self.store.update_reminders({"enabled": False})
        self.assertIsNone(self.store.due_reminder())
        self.store.update_reminders({"enabled": True})
        self.store.pause_reminders(30)
        self.assertIsNone(self.store.due_reminder())
        self.assertEqual(self.store.reminders()["paused_until"] > time.time(), True)


class NoteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = CompanionStore(Path(self.temporary.name) / "state/notifications.sqlite3")

    def test_notes_are_daily_toggleable_and_validated(self):
        note = self.store.add_note("  写测试  ")
        self.assertEqual(note["text"], "写测试")
        self.assertEqual(len(self.store.notes()), 1)
        self.assertTrue(self.store.toggle_note(note["id"])["done"])
        self.assertFalse(self.store.toggle_note(note["id"])["done"])
        for text in ("", "x" * 121):
            with self.assertRaises(ValueError):
                self.store.add_note(text)
        self.store.remove_note(note["id"])
        self.assertEqual(self.store.notes(), [])
        self.assertEqual(self.store.notes("2020-01-01"), [])


class AffectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = CompanionStore(Path(self.temporary.name) / "state/notifications.sqlite3")

    def test_stage_thresholds_and_day_count(self):
        self.assertEqual(stage_for(0)["name"], "初识")
        self.assertEqual(stage_for(30)["name"], "熟悉")
        self.assertEqual(stage_for(10_000)["name"], "挚友")
        self.assertIsNone(stage_for(10_000)["next_at"])
        view = self.store.record_interaction("pet")
        self.assertEqual(view["points"], 1)
        self.assertEqual(view["days"], 1)
        self.assertTrue(0.0 <= view["stage"]["progress"] <= 1.0)

    def test_snapshot_combines_every_phase_one_section(self):
        snapshot = self.store.snapshot()
        self.assertEqual({"pomodoro", "reminders", "notes", "affection"}, set(snapshot))


if __name__ == "__main__":
    unittest.main()
