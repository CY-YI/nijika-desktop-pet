"""Release boundaries: data-only skins, portable sponsor info and safe adapters."""
import hashlib
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace
from zipfile import ZipFile

from PIL import Image, ImageDraw

from agent_setup import AgentSetup
from control_panel import skin_idle_preview
from control_store import ControlStore, SPRITES
from notification_store import NotificationStore
from skin_animation import SkinTimeline, validate_animation
from support_bundle import read_bundle
from tools import package_release

ROOT = Path(__file__).resolve().parents[1]


def png(offset=0):
    image = Image.new("RGBA", (64, 96))
    ImageDraw.Draw(image).ellipse((16 + offset, 20, 40 + offset, 80), fill="gold")
    result = io.BytesIO()
    image.save(result, format="PNG")
    return result.getvalue()


def pack(manifest=None, extra=None):
    output = io.BytesIO()
    manifest = manifest or {"name": "Test character", "idle": {
        "frames": ["idle_000.png", "idle_001.png"], "durations_ms": [120, 80]}}
    with ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("idle_000.png", png())
        archive.writestr("idle_001.png", png(3))
        for name, value in (extra or {}).items():
            archive.writestr(name, value)
    return output.getvalue()


class ReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.public = self.base / "application"
        self.store = ControlStore(self.base / "state/notices.sqlite3", public_root=self.public)

    def test_animated_skin_autofills_expressions_and_obeys_exact_timing(self):
        skin = self.store.import_skin(pack(), "my-character.zip")
        directory = self.store.skin_directory(skin["id"])
        self.assertEqual(skin["kind"], "animated")
        self.assertEqual(len(list(directory.glob("*.png"))), 11)
        self.assertTrue(set(SPRITES).issubset({item.stem for item in directory.glob("*.png")}))
        timeline = SkinTimeline.load(directory)
        self.assertEqual([timeline.frame(t) for t in (0, .119, .120, .199, .200, 1.120)],
                         ["idle_000", "idle_000", "idle_001", "idle_001", "idle_000", "idle_001"])
        with Image.open(io.BytesIO(skin_idle_preview(str(directory)))) as image:
            self.assertEqual(image.n_frames, 2)
            image.seek(1)
            self.assertEqual(image.mode, "RGBA")
        self.assertEqual(self.store.skins()[1]["idle"], skin["idle"])
        self.store.update_settings({"skin": skin["id"]})
        (directory / "idle_001.png").unlink()
        with self.assertRaises(ValueError):
            self.store.skin_directory(skin["id"])

    def test_native_animation_preloads_and_never_reads_disk_during_render(self):
        import ctypes
        from pet import SpriteSet
        skin = self.store.import_skin(pack(), "native.zip")
        sprites = SpriteSet(260, 390, self.store.skin_directory(skin["id"]))
        try:
            with patch("PIL.Image.open", side_effect=AssertionError("render must not read files")):
                sprites.render("idle_000")
                first = ctypes.string_at(sprites.bits, 260 * 390 * 4)
                sprites.render("idle_001")
                second = ctypes.string_at(sprites.bits, 260 * 390 * 4)
            self.assertNotEqual(first, second)
        finally:
            sprites.close()

    def test_desktop_tick_uses_timeline_and_yields_to_motion_off_and_interactions(self):
        from pet import PetWindow
        window = object.__new__(PetWindow)
        window.state, window.motion_mode = "curious", "lively"
        window.motion_started = window.last_tick = 0
        window.bubble = SimpleNamespace(tick=Mock())
        window.chat_enabled = False
        window._render_interaction = Mock(return_value=False)
        window.sprites = SimpleNamespace(timeline=SkinTimeline({"frames": ["idle_000.png", "idle_001.png"], "durations_ms": [120, 80]}))
        window.next_blink = window.next_wink = window.next_idle_hop = 999
        window.blink_until = window.wink_until = window.bounce_started = window.drag_tilt = window.drag_direction = 0
        window.drag_start, window.badge_cache = None, None
        window.show_pose = Mock()
        with patch("pet.time.monotonic", return_value=.13):
            window.tick()
            self.assertEqual(window.show_pose.call_args.args[0], "idle_001")
            window.motion_mode = "off"
            window.tick()
            self.assertEqual(window.show_pose.call_args.args[0], "curious")
            window.show_pose.reset_mock()
            window._render_interaction.return_value = True
            window.tick()
            window.show_pose.assert_not_called()

    def test_skin_rejects_scripts_extra_frames_and_timeline_errors_before_install(self):
        for extra in ({"../curious.png": png()}, {"code.js": b"alert(1)"},
                      {"idle_002.png": png()}, {"nested/manifest.json": b"{}"}):
            with self.subTest(extra=list(extra)), self.assertRaises(ValueError):
                self.store.import_skin(pack(extra=extra), "bad.zip")
        for value in ({}, {"frames": ["../bad.png"] * 2, "durations_ms": [100, 100]},
                      {"frames": ["idle_000.png", "idle_001.png"], "durations_ms": [True, 80]},
                      {"frames": ["idle_000.png", "idle_001.png"], "durations_ms": [0, 80]},
                      {"frames": ["idle_000.png", "idle_001.png"], "durations_ms": [80]},
                      {"frames": ["idle_000.png", "idle_001.png"], "durations_ms": [5001, 80]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_animation(value)
        self.assertEqual(len(self.store.skins()), 1)

    def test_skin_aggregate_pixel_limit_and_failed_write_leave_no_skin(self):
        data = pack()
        with patch("control_store.MAX_PIXELS", 1000), self.assertRaises(ValueError):
            self.store.import_skin(data, "too-large.zip")
        with patch("PIL.Image.Image.save", side_effect=OSError("test write failure")), self.assertRaises(OSError):
            self.store.import_skin(data, "write-failed.zip")
        self.assertEqual(len(self.store.skins()), 1)
        self.assertEqual(list((self.store.root / "skins").glob("*")), [])

    def test_public_support_roundtrip_local_override_and_safe_packaging(self):
        config = {"name": "Demo author", "message": "Voluntary support", "url": "https://example.com/sponsor"}
        self.store.update_support(config)
        self.store.save_support_image(png())
        data = self.store.export_support()
        public_files = read_bundle(data)
        self.assertEqual(set(public_files), {"distribution/support.json", "distribution/support.png"})
        for name, value in public_files.items():
            target = self.public / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
        recipient = ControlStore(self.base / "recipient/notices.sqlite3", public_root=self.public)
        self.assertEqual(recipient.support(), {**config, "has_image": True})
        self.assertEqual(recipient.agents(), [])
        recipient.update_support({**config, "message": "Local preference"})
        self.assertEqual(recipient.support()["message"], "Local preference")
        self.assertEqual(self.store.support()["message"], "Voluntary support")
        # A link-only update must not accidentally show an old recipient QR file.
        (self.public / "distribution/support.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertFalse(recipient.support()["has_image"])
        (self.public / "distribution/support.json").write_text("42", encoding="utf-8")
        self.assertFalse(recipient.support()["has_image"])
        bundle = self.base / "public.zip"
        bundle.write_bytes(data)
        source = self.base / "mock-source"
        source.mkdir()
        (source / "app.exe").write_bytes(b"test executable placeholder")
        output = self.base / "release.zip"
        with patch.object(package_release, "ROOT", source), patch.object(package_release, "FILES", ("app.exe",)):
            package_release.build(output, support_bundle=bundle)
        with ZipFile(output) as archive:
            manifest = json.loads(archive.read(package_release.PREFIX + "/SHA256SUMS.json"))
            self.assertEqual(set(manifest), {"app.exe", *public_files})
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(archive.read(package_release.PREFIX + "/" + name)).hexdigest(), digest)
            self.assertFalse(any("sqlite" in name or "agents" in name for name in archive.namelist()))

    def test_empty_or_unsafe_public_support_cannot_be_exported(self):
        with self.assertRaises(ValueError):
            self.store.export_support()
        for link in ("file:///private", "javascript:alert(1)", "https://name:password@example.com",
                     "https://example.com/\nprivate", "https://[broken"):
            with self.subTest(link=link), self.assertRaises(ValueError):
                self.store.update_support({"name": "Test", "message": "", "url": link})
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr("distribution/support.json", json.dumps({"name": "Test", "message": "", "url": "https://example.com"}))
            archive.writestr("../private.sqlite3", "private")
        with self.assertRaises(ValueError):
            read_bundle(output.getvalue())

    def test_codex_unknown_same_name_service_not_modified(self):
        home = self.base / "user"
        directory = home / ".codex"
        directory.mkdir(parents=True)
        unknown = self.base / "unknown.exe"
        unknown.write_bytes(b"not nijika")
        original = '[mcp_servers.nijika-pet]\ncommand = ' + json.dumps(str(unknown))
        config = directory / "config.toml"
        config.write_text(original, encoding="utf-8")
        setup = AgentSetup(ROOT, self.store, home)
        with self.assertRaisesRegex(ValueError, "未知服务"):
            setup.plan("codex", "Codex")
        self.assertEqual(config.read_text(encoding="utf-8"), original)
        self.assertFalse((directory / "AGENTS.md").exists())
        self.assertTrue(all("capabilities" in item for item in setup.clients()))

    def test_simultaneous_same_question_and_out_of_order_replies_do_not_cross(self):
        stores = [NotificationStore(self.base / "queue.sqlite3") for _ in range(12)]
        def create(index):
            return stores[index].create("Codex" if index % 2 == 0 else "DSH", "相同问题", "优先处理哪项？", [
                {"label": "界面", "description": "优先检查界面交互效果。"},
                {"label": "接口", "description": "优先检查接口回执结果。"}])
        with ThreadPoolExecutor(max_workers=6) as pool:
            notices = list(pool.map(create, range(len(stores))))
        self.assertEqual(len({item.id for item in notices}), len(stores))
        for index in reversed(range(len(stores))):
            stores[0].answer(notices[index].id, index % 2)
        for index, item in enumerate(notices):
            reply = stores[index].get(item.id)
            self.assertEqual(reply.agent, "Codex" if index % 2 == 0 else "DSH")
            self.assertEqual(reply.result()["choice"], "界面" if index % 2 == 0 else "接口")
