"""Real VP9 alpha roundtrip and read-only/ranged review HTTP checks."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw
from tools.prepare_animation import prepare, file_hash
from tools.review_animation import export_review, ReviewServer

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


@unittest.skipUnless(imageio_ffmpeg, "Install tools/requirements-animation.txt")
class AnimationReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="nijika-review-test-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.source = cls.root / "original.mkv"
        writer = imageio_ffmpeg.write_frames(str(cls.source), (64, 96), fps=4, codec="ffv1",
                                            pix_fmt_out="bgr0", macro_block_size=1, ffmpeg_log_level="error")
        writer.send(None)
        try:
            for index in range(8):
                frame = Image.new("RGB", (64, 96), (0, 0, 255))
                draw = ImageDraw.Draw(frame)
                draw.rectangle((15, 25, 50, 80), fill=(40, 160, 90))
                draw.rectangle((18 + index, 40, 23 + index, 45), fill=(230, 100, 90))
                draw.rectangle((52, 8, 60, 14), fill="white")
                writer.send(frame.tobytes())
        finally:
            writer.close()
        cls.preview = cls.root / "preview.webp"
        prepare(cls.source, cls.preview, width=64, max_seconds=2, loop_mode="ping-pong")
        cls.before = {path: file_hash(path) for path in (cls.source, cls.preview)}
        cls.directory = cls.root / "review"
        cls.manifest = export_review(cls.source, cls.preview, cls.directory)

    def test_real_video_roundtrip_retains_alpha_color_marker_and_frame_order(self):
        manifest = self.manifest
        self.assertTrue(manifest["preview_only"])
        self.assertEqual(manifest["visual_acceptance"], "pending")
        self.assertEqual(manifest["frames"], 14)
        self.assertEqual(manifest["fps"], 4)
        self.assertEqual(manifest["python_frame_buffer_bytes"], 64 * 96 * 4)
        for item in manifest["files"].values():
            self.assertAlmostEqual(item["duration_seconds"], 3.5, delta=0.011)
        self.assertEqual(set(manifest["posters"]), {"source-poster.png", "transparent-poster.png"})
        for poster in manifest["posters"]:
            self.assertGreater(manifest["posters"][poster]["bytes"], 100)
        for path, digest in self.before.items():
            self.assertEqual(file_hash(path), digest)
        reader = imageio_ffmpeg.read_frames(str(self.directory / "transparent.webm"), pix_fmt="rgba",
                                           bits_per_pixel=32, input_params=["-c:v", "libvpx-vp9"])
        next(reader)
        try:
            decoded = [Image.frombytes("RGBA", (64, 96), pixels) for pixels in reader]
        finally:
            reader.close()
        self.assertEqual(len(decoded), 14)
        for frame in decoded:
            self.assertEqual(frame.getpixel((2, 2))[3], 0)
            self.assertGreater(frame.getpixel((56, 10))[3], 245)
            self.assertTrue(all(value > 235 for value in frame.getpixel((56, 10))[:3]))
            actual = frame.getpixel((40, 60))
            self.assertTrue(all(abs(left - right) < 12 for left, right in zip(actual, (40, 160, 90, 255))))
        # Forward starts at source 1, reverse ends at 0. VP9 4:2:0 blends
        # chroma at the square's boundary; use its weighted red center.
        def red_center(frame):
            weights = [(x, max(0, frame.getpixel((x, 42))[0] - frame.getpixel((x, 42))[1]))
                       for x in range(14, 38)]
            return sum(x * weight for x, weight in weights) / sum(weight for _, weight in weights)
        self.assertAlmostEqual(red_center(decoded[0]) - red_center(decoded[-1]), 1, delta=0.25)
        self.assertFalse(manifest["files"]["source.webm"]["has_alpha"])

    def test_existing_output_and_changed_source_are_refused(self):
        with self.assertRaises(FileExistsError):
            export_review(self.source, self.preview, self.directory)
        changed = self.root / "changed.mkv"
        changed.write_bytes(b"unrelated source")
        destination = self.root / "not-created"
        with self.assertRaisesRegex(ValueError, "hash"):
            export_review(changed, self.preview, destination)
        self.assertFalse(destination.exists())

    def test_authored_pause_is_not_silently_converted_to_constant_fps(self):
        target = self.root / "paused.webp"
        with Image.open(self.preview) as source:
            frames = []
            for index in range(source.n_frames):
                source.seek(index)
                frames.append(source.convert("RGBA"))
        frames[0].save(target, save_all=True, append_images=frames[1:],
                       duration=[500] + [250] * 13, loop=0, lossless=True)
        report = json.loads(self.preview.with_suffix(".webp.json").read_text(encoding="utf-8"))
        report["output_sha256"] = file_hash(target)
        target.with_suffix(".webp.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "authored pauses"):
            export_review(self.source, target, self.root / "not-paused-export")

    def test_read_only_server_supports_video_seek_and_rejects_cross_site_and_paths(self):
        with ReviewServer(self.directory) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(server.origin, timeout=5) as response:
                    self.assertIn(b"/review.js", response.read())
                    self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
                    self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
                original = (self.directory / "transparent.webm").read_bytes()
                for header, expected in (("bytes=0-31", original[:32]), ("bytes=-17", original[-17:]),
                                         (f"bytes={len(original)-12}-", original[-12:])):
                    with urlopen(Request(server.origin + "/transparent.webm", headers={"Range": header}), timeout=5) as response:
                        self.assertEqual(response.status, 206)
                        self.assertEqual(response.read(), expected)
                for poster in ("source-poster.png", "transparent-poster.png"):
                    with urlopen(server.origin + "/" + poster, timeout=5) as response:
                        self.assertEqual(response.headers["Content-Type"], "image/png")
                        self.assertGreater(len(response.read()), 100)
                for path, headers, status in (
                        ("/transparent.webm", {"Range": "bytes=999999999-"}, 416),
                        ("/transparent.webm", {"Range": "bytes=0-1,3-4"}, 416),
                        ("/review.json", {"Origin": "https://example.com"}, 403),
                        ("/review.json", {"Sec-Fetch-Site": "cross-site"}, 403),
                        ("/review.json", {"Host": "attacker.invalid"}, 403),
                        ("/../review.json", {}, 404), ("/%2e%2e/review.json", {}, 404)):
                    with self.subTest(path=path, headers=headers), self.assertRaises(HTTPError) as error:
                        urlopen(Request(server.origin + path, headers=headers), timeout=5)
                    self.assertEqual(error.exception.code, status)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(server.origin + "/review.json", data=b"{}"), timeout=5)
                self.assertEqual(error.exception.code, 501)
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
