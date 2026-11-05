"""Actual lossless video/alpha roundtrip, low-FPS and no-overwrite checks."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from tools.prepare_animation import prepare, file_hash

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


@unittest.skipUnless(imageio_ffmpeg, "Install tools/requirements-animation.txt for video conversion checks")
class AnimationPreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nijika-video-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "blue source.mkv"
        writer = imageio_ffmpeg.write_frames(str(self.source), (64, 96), fps=4, codec="ffv1",
                                            pix_fmt_out="bgr0", macro_block_size=1, ffmpeg_log_level="error")
        writer.send(None)
        try:
            for index in range(12):
                image = Image.new("RGB", (64, 96), (0, 0, 255))
                draw = ImageDraw.Draw(image)
                draw.rectangle((15, 25, 50, 80), fill=(40, 160, 90))
                draw.rectangle((18 + index, 40, 23 + index, 45), fill=(230, 100, 90))
                writer.send(image.tobytes())
        finally:
            writer.close()

    def test_real_video_preserves_green_removes_blue_and_never_upsamples(self):
        before = file_hash(self.source)
        target = self.root / "preview.webp"
        report = prepare(self.source, target, width=64, max_seconds=2)
        self.assertEqual(file_hash(self.source), before)
        self.assertEqual(report["source_fps"], 4)
        self.assertEqual(report["sample_fps"], 4)
        self.assertTrue(report["preview_only"])
        self.assertEqual(report["visual_acceptance"], "pending")
        self.assertGreaterEqual(report["unique_frames"], 6)
        self.assertAlmostEqual(report["duration_ms"], 2000, delta=60)
        with Image.open(target) as image:
            for index in range(image.n_frames):
                image.seek(index)
                rgba = image.convert("RGBA")
                self.assertEqual(rgba.getpixel((2, 2))[3], 0)
                self.assertEqual(rgba.getpixel((40, 60)), (40, 160, 90, 255))

    def test_preexisting_preview_and_report_are_not_overwritten(self):
        target = self.root / "keep.webp"
        target.write_bytes(b"keep existing preview")
        with self.assertRaises(FileExistsError):
            prepare(self.source, target)
        self.assertEqual(target.read_bytes(), b"keep existing preview")
        other = self.root / "other.webp"
        sidecar = other.with_suffix(".webp.json")
        sidecar.write_bytes(b"keep report")
        with self.assertRaises(FileExistsError):
            prepare(self.source, other)
        self.assertFalse(other.exists())
        self.assertEqual(sidecar.read_bytes(), b"keep report")

    def test_observed_blue_key_keeps_green_and_white_overlay(self):
        source = self.root / "observed blue.mkv"
        writer = imageio_ffmpeg.write_frames(str(source), (64, 96), fps=4, codec="ffv1",
                                            pix_fmt_out="bgr0", macro_block_size=1, ffmpeg_log_level="error")
        writer.send(None)
        try:
            for index in range(8):
                frame = Image.new("RGB", (64, 96), (62, 144, 205))
                draw = ImageDraw.Draw(frame)
                draw.rectangle((15, 25, 50, 80), fill=(40, 160, 90))
                draw.rectangle((18 + index, 40, 23 + index, 45), fill=(230, 100, 90))
                draw.rectangle((52, 8, 60, 12), fill="white")
                draw.rectangle((27, 82, 36, 91), fill=(32, 21, 75))
                draw.rectangle((2, 82, 10, 89), fill=(160, 190, 225))
                writer.send(frame.tobytes())
        finally:
            writer.close()
        target = self.root / "observed.webp"
        report = prepare(source, target, width=64, key_color="#3e90cd", clean_blue_shadows=True,
                         shadow_region=(0.40, 0.83, 0.60, 0.97))
        self.assertEqual(report["key_color"], "#3E90CD")
        with Image.open(target) as image:
            rgba = image.convert("RGBA")
            self.assertEqual(rgba.getpixel((2, 2))[3], 0)
            self.assertEqual(rgba.getpixel((40, 60)), (40, 160, 90, 255))
            self.assertEqual(rgba.getpixel((56, 10)), (255, 255, 255, 255))
            self.assertEqual(rgba.getpixel((30, 86))[3], 0)
            self.assertEqual(rgba.getpixel((5, 85))[3], 255)

    def test_ping_pong_visits_endpoints_once_without_upsampling_or_extra_hold(self):
        target = self.root / "loop.webp"
        report = prepare(self.source, target, width=64, max_seconds=2, loop_mode="ping-pong")
        self.assertEqual(report["sample_fps"], 4)
        self.assertEqual(report["loop_mode"], "ping-pong")
        self.assertEqual(report["ping_pong_endpoints"], "single")
        # Eight source frames: 1..7, 6..0. No doubled end frame at
        # the turnaround or at the loop boundary (14 frames / 4 FPS).
        self.assertAlmostEqual(report["duration_ms"], 3500, delta=60)
        with Image.open(target) as image:
            self.assertEqual(image.n_frames, 14)
            for index in range(image.n_frames):
                image.seek(index)
                image.load()
                self.assertEqual(image.info["duration"], 250)
            image.seek(0)
            first = image.convert("RGBA")
            image.seek(image.n_frames - 1)
            last = image.convert("RGBA")
            # The moving red square ends at source 0 and starts at source 1;
            # the loop crossing is one authored step, not a held duplicate.
            self.assertEqual(first.getpixel((18, 42)), (40, 160, 90, 255))
            self.assertEqual(last.getpixel((18, 42)), (230, 100, 90, 255))

    def test_invalid_processing_limits_leave_source_and_directory_unchanged(self):
        before = file_hash(self.source)
        target = self.root / "new/preview.webp"
        for settings in ({"width": 8000}, {"fps_cap": 0}, {"max_seconds": 600}, {"similarity": 1},
                         {"key_color": "#00FF00"}, {"key_color": "bad"}, {"key_color": "#ZZZZZZ"},
                         {"clean_blue_shadows": True}, {"loop_mode": "crossfade"},
                         {"clean_blue_shadows": True,"shadow_region": (0.5,0.9,0.4,0.8)}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                prepare(self.source, target, **settings)
        self.assertFalse(target.parent.exists())
        self.assertEqual(file_hash(self.source), before)


if __name__ == "__main__":
    unittest.main()
