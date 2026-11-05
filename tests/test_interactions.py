"""Optional care transactions and preview isolation at the local HTTP boundary."""
from __future__ import annotations

import io
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from PIL import Image
from control_panel import ControlApplication, ControlServer
from interaction_motion import ACTIONS, motion_at, render_interaction, preview_webp
from interaction_store import InteractionStore

ROOT = Path(__file__).resolve().parents[1]


class CareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "queue.sqlite3"
        self.store = InteractionStore(self.database)

    def test_optional_values_pause_and_offline_decay_is_bounded(self):
        self.assertFalse(self.store.snapshot(10000)["enabled"])
        self.assertEqual(self.store.snapshot(20000)["satiety"], 80)
        self.store.configure({"enabled": True}, 20000)
        later = self.store.snapshot(20000 + 3600 * 100)
        self.assertEqual([later[key] for key in ("satiety", "hydration", "mood")], [56, 48, 68])
        self.store.configure({"enabled": False}, 380000)
        self.assertEqual(self.store.snapshot(10**9)["satiety"], 56)

    def test_feeding_caps_values_and_rejected_requests_do_not_mutate(self):
        with self.assertRaises(ValueError):
            self.store.feed("feed", 10000)
        self.store.configure({"enabled": True}, 10000)
        result = self.store.feed("feed", 10000)
        self.assertEqual(result["care"]["satiety"], 100)
        self.assertEqual(result["care"]["mood"], 84)
        self.assertEqual(result["status"], "applied")
        before = self.database.read_bytes()
        with self.assertRaises(ValueError):
            self.store.feed("feed", 10001)
        self.assertEqual(self.database.read_bytes(), before)
        self.store.feed("drink", 10001)
        self.assertEqual(self.store.snapshot(10001)["drink_wait"], 30)
        self.assertEqual(self.store.snapshot(10001)["feed_wait"], 29)
        self.store.feed("feed", 10030)

    def test_feeding_publishes_one_desktop_action_revision(self):
        self.store.configure({"enabled": True}, 10000)
        first = self.store.snapshot(10000)
        self.assertEqual((first["action_revision"], first["last_action"]), (0, ""))
        self.store.feed("feed", 10000)
        feed = self.store.snapshot(10000)
        self.assertEqual((feed["action_revision"], feed["last_action"]), (1, "feed"))
        self.store.feed("drink", 10001)
        drink = self.store.snapshot(10001)
        self.assertEqual((drink["action_revision"], drink["last_action"]), (2, "drink"))

    def test_fast_feed_and_drink_are_claimed_in_order_once_across_instances(self):
        self.store.configure({"enabled": True}, 10000)
        self.store.feed("feed", 10000)
        self.store.feed("drink", 10000)
        self.assertNotIn("_desktop_actions", self.store.snapshot(10000))
        first = InteractionStore(self.database).take_action(10001)
        second = InteractionStore(self.database).take_action(10001)
        self.assertEqual([first["action"], second["action"]], ["feed", "drink"])
        self.assertIsNone(self.store.take_action(10001))

    def test_cosmetic_actions_expire_or_cancel_when_care_is_disabled(self):
        self.store.configure({"enabled": True}, 10000)
        self.store.feed("feed", 10000)
        self.assertIsNone(self.store.take_action(10031))
        self.store.feed("drink", 10032)
        self.store.configure({"enabled": False}, 10033)
        self.store.configure({"enabled": True}, 10034)
        self.assertIsNone(self.store.take_action(10034))
        self.assertGreater(self.store.snapshot(10034)["hydration"], 99)

    def test_parallel_feeds_only_apply_once_and_clock_rollback_does_not_double_decay(self):
        self.store.configure({"enabled": True}, 10000)
        def feed():
            try:
                return InteractionStore(self.database).feed("feed", 10001)["status"]
            except ValueError:
                return "cooldown"
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(lambda _: feed(), range(2))), ["applied", "cooldown"])
        future = self.store.snapshot(13600)
        self.store.snapshot(11000)
        self.assertEqual(self.store.snapshot(13600)["satiety"], future["satiety"])

    def test_strict_settings_and_no_separate_desktop_action_table(self):
        for patch_data in ({}, {"enabled":"yes"}, {"touch_enabled":1}, {"satiety":100}, {"unknown":True}):
            with self.assertRaises(ValueError):
                self.store.configure(patch_data, 10000)
        for action in ("dance", "../../run", None, {}):
            with self.assertRaises(ValueError):
                self.store.feed(action, 10000)
        self.store.configure({"touch_enabled":False}, 10000)
        self.assertFalse(InteractionStore(self.database).snapshot(10000)["touch_enabled"])
        with self.store._connect() as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("pet_actions", names)


class MotionTests(unittest.TestCase):
    def test_all_actions_return_to_neutral_and_deform_only_locally(self):
        source = Image.new("RGBA", (80,120))
        for y in range(10,115):
            for x in range(10,75):
                source.putpixel((x,y), (x,y,100,255))
        for action, (_, duration, _, _) in ACTIONS.items():
            self.assertFalse(any(motion_at(action, 0).values()))
            self.assertFalse(any(motion_at(action, duration).values()))
            self.assertEqual(render_interaction(source, action, 0).tobytes(), source.tobytes())
            frame = render_interaction(source, action, duration * .4)
            self.assertNotEqual(frame.tobytes(), source.tobytes())
            self.assertEqual(frame.size, source.size)
            self.assertEqual(frame.getpixel((0,0))[3], 0)
        self.assertEqual(render_interaction(source, "dance", .7, 0).tobytes(), source.tobytes())

    def test_encoded_preview_is_one_cycle_with_transparent_frames(self):
        source = Image.new("RGBA", (48,72))
        source.paste((240,170,90,255), (14,15,34,65))
        data = preview_webp(source, "pet", .5, False)
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.info["loop"], 1)
            self.assertTrue(image.is_animated)
            self.assertGreater(image.n_frames, 30)
            self.assertEqual(image.size, source.size)
            image.seek(image.n_frames - 1)
            self.assertEqual(image.convert("RGBA").getpixel((0,0))[3], 0)


class InteractionAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.app = ControlApplication(base / "state/notifications.sqlite3", ROOT, base / "user")
        self.server = ControlServer(self.app)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, route, payload=None, token=True, origin=None):
        headers = {"X-Nijika-Token": self.server.token} if token else {}
        if origin:
            headers["Origin"] = origin
        request = Request(self.server.origin + route, json.dumps(payload).encode() if payload is not None else None, headers)
        return urlopen(request, timeout=10)

    def test_preview_auth_parameters_and_care_isolation(self):
        with self.call("/api/state") as response:
            self.assertFalse(json.load(response)["interaction"]["desktop_playback"])
        with patch("control_panel.interaction_preview", return_value=b"webp-preview") as generate:
            for route, token, origin in (
                ("/api/interaction-preview/pet.webp", False, None),
                ("/api/interaction-preview/pet.webp", True, "https://example.com"),
                ("/api/interaction-preview/invalid.webp", True, None),
                ("/api/interaction-preview/pet.webp?strength=huge", True, None),
                ("/api/interaction-preview/pet.webp?effects=false", True, None),
                ("/api/interaction-preview/pet.webp?skin=../../", True, None),
                ("/api/interaction-preview/pet.webp?effects=0&effects=1", True, None),
            ):
                with self.assertRaises(HTTPError):
                    self.call(route, token=token, origin=origin)
            generate.assert_not_called()
            before = self.app.interaction.snapshot()
            with self.call("/api/interaction-preview/pet.webp?strength=gentle&effects=0") as response:
                self.assertEqual(response.headers["Content-Type"], "image/webp")
                self.assertEqual(response.read(), b"webp-preview")
            self.assertEqual(self.app.interaction.snapshot()["satiety"], before["satiety"])
            self.assertIsNone(self.app.notifications.next_pending())

    def test_state_exposes_desktop_playback_when_renderer_is_alive(self):
        status = self.app.store.root / "renderer-status.json"
        status.write_text(json.dumps({"heartbeat_at": time.time(), "window_visible": True,
                                      "desktop_playback": True, "supports_control": True,
                                      "applied_revision": 0}), encoding="utf-8")
        with self.call("/api/state") as response:
            state = json.load(response)
        self.assertTrue(state["renderer"]["desktop_playback"])
        self.assertTrue(state["interaction"]["desktop_playback"])
        status.write_text(json.dumps({"heartbeat_at": time.time() - 30, "desktop_playback": True}), encoding="utf-8")
        self.assertFalse(self.app.state()["interaction"]["desktop_playback"])

    def test_settings_round_trip_feeding_and_unknown_actions_rejected(self):
        with self.call("/api/interaction", {"enabled":True, "effects_enabled":False}) as response:
            self.assertTrue(json.load(response)["enabled"])
        for payload, token in (({"enabled":"yes"},True), ({"enabled":True},False),
                               ({"action":"dance"},True), ({"action":"feed","enabled":True},True)):
            with self.assertRaises(HTTPError):
                self.call("/api/interaction", payload, token=token)
        with self.call("/api/interaction", {"action":"feed"}) as response:
            self.assertEqual(json.load(response)["status"], "applied")
        with self.assertRaises(HTTPError):
            self.call("/api/interaction", {"action":"feed"})
        with self.call("/api/state") as response:
            care = json.load(response)["interaction"]
        self.assertFalse(care["effects_enabled"])
        self.assertGreater(care["satiety"], 99)
        with self.call("/interaction.js") as response:
            self.assertIn(b"previewAnimation", response.read())
