"""Desktop routing: cosmetic actions must yield to real Agent notices."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from interaction_motion import ACTIONS, hit_region
from interaction_store import InteractionStore
from pet import PetWindow, BubbleNotice


def window_without_native_surface():
    window = object.__new__(PetWindow)
    window.width, window.height = 320, 480
    window.state, window.motion_mode = "curious", "lively"
    window.badge_cache = None
    window.bubble = SimpleNamespace(notice=None)
    window.active_notice_id = None
    window.drag_start = None
    window.interaction_action = None
    window.interaction_snapshot = {"enabled": False, "touch_enabled": True, "effects_enabled": True}
    window.next_interaction_poll = window.last_interaction_error_at = 0
    window.show_pose = Mock()
    window.tick = Mock()
    return window


class PetInteractionTests(unittest.TestCase):
    def test_touch_is_independent_of_care_and_finishes_at_persistent_expression(self):
        window = window_without_native_surface()
        self.assertEqual([hit_region(.5, y) for y in (.2, .4, .7)], ["pet", "poke", "nod"])
        with patch("pet.time.monotonic", return_value=10):
            window.start_interaction("pet")
        self.assertEqual(window.interaction_action, "pet")
        self.assertEqual(window.state, "curious")
        self.assertTrue(window._render_interaction(10.8))
        self.assertEqual(window.show_pose.call_args.args[0], "happy")
        self.assertFalse(window._render_interaction(10 + ACTIONS["pet"][1]))
        self.assertIsNone(window.interaction_action)
        self.assertEqual(window.state, "curious")
        window.tick.assert_called_once()  # No recursive tick at the end.

    def test_disabled_touch_and_active_agent_notice_reject_cosmetic_actions(self):
        window = window_without_native_surface()
        window.interaction_snapshot["touch_enabled"] = False
        window.start_interaction("pet")
        self.assertIsNone(window.interaction_action)
        window.active_notice_id = "pending-agent"
        window.start_interaction("dance")
        self.assertIsNone(window.interaction_action)
        window.active_notice_id = None
        window.bubble.notice = BubbleNotice("权限", "在原卡片授权", kind="approval")
        window.start_interaction("shake")
        self.assertIsNone(window.interaction_action)

    def test_off_mode_is_static_and_effect_switch_removes_sparkle(self):
        window = window_without_native_surface()
        window.motion_mode = "off"
        with patch("pet.time.monotonic", return_value=10):
            window.start_interaction("dance")
        window._render_interaction(11)
        pose = window.show_pose.call_args.kwargs
        self.assertEqual((pose["angle"], pose["shift_y"], pose["scale_x"], pose["scale_y"], pose["sparkle"]),
                         (0, 0, 1, 1, 0))
        window.motion_mode = "lively"
        window.interaction_snapshot["effects_enabled"] = False
        window._render_interaction(11)
        self.assertEqual(window.show_pose.call_args.kwargs["sparkle"], 0)
        window.stop_interaction()
        self.assertFalse(window._render_interaction(11))

    def test_poll_keeps_recent_feeding_queued_while_an_agent_needs_attention(self):
        with tempfile.TemporaryDirectory() as directory:
            store = InteractionStore(Path(directory) / "test.sqlite3")
            store.configure({"enabled": True}, 10000)
            store.feed("feed", 10000)
            store.feed("drink", 10000)
            window = window_without_native_surface()
            window.interaction = store
            window.start_interaction = Mock()
            window.active_notice_id = "permission-request"
            with patch("interaction_store.time.time", return_value=10001):
                window._poll_interaction(100)
                window.start_interaction.assert_not_called()
                window.active_notice_id = None
                window._poll_interaction(101)
                window._poll_interaction(102)
                window._poll_interaction(103)
            self.assertEqual([call.args[0] for call in window.start_interaction.call_args_list], ["feed", "drink"])

    def test_database_failure_backs_off_without_consuming_actions(self):
        window = window_without_native_surface()
        window.interaction = Mock()
        window.interaction.snapshot.side_effect = sqlite3.OperationalError("busy")
        with patch("pet.log_notice_event"):
            window._poll_interaction(100)
        self.assertGreaterEqual(window.next_interaction_poll, 105)
        window.interaction.take_action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
