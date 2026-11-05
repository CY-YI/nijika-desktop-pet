"""Export synchronized review videos and serve a read-only loopback comparison.

Uses existing, provenance-checked WebP/source files. Does not generate artwork,
install a skin, alter notification data, or approve visual quality.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.prepare_animation import file_hash

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "art" / "animation" / "review"
CODEC_OPTIONS = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "20",
                 "-deadline", "good", "-cpu-used", "4", "-threads", "2",
                 "-row-mt", "1", "-auto-alt-ref", "0", "-an", "-sn"]


def decode_metrics(path: Path) -> dict:
    """Force libvpx: FFmpeg's native VP9 decoder may discard the alpha plane."""
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgba", bits_per_pixel=32,
                                       input_params=["-c:v", "libvpx-vp9"])
    try:
        meta = next(reader)
        count, transparent = 0, False
        for pixels in reader:
            count += 1
            transparent |= min(pixels[3::4]) < 255
        return {"frames": count, "size": list(meta["size"]), "fps": meta["fps"],
                "duration_seconds": meta["duration"], "has_alpha": transparent}
    finally:
        reader.close()


def write_poster(path: Path, destination: Path) -> None:
    """Decode and save one poster frame for browsers before video composition."""
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgba", bits_per_pixel=32,
                                       input_params=["-c:v", "libvpx-vp9"])
    try:
        metadata = next(reader)
        pixels = next(reader)
    finally:
        reader.close()
    Image.frombytes("RGBA", metadata["size"], pixels).save(destination, format="PNG", optimize=True)


def export_review(source: Path, preview: Path, destination: Path) -> dict:
    """Stream RGBA frames to the encoder, holding no list of decoded images."""
    import imageio_ffmpeg
    source, preview = source.resolve(strict=True), preview.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError("Choose a new review directory; existing files are preserved.")
    report = json.loads(preview.with_suffix(preview.suffix + ".json").read_text(encoding="utf-8"))
    if report.get("input_sha256") != file_hash(source) or report.get("output_sha256") != file_hash(preview):
        raise ValueError("Source/preview hashes do not match the preparation report.")
    fps = report.get("sample_fps", 0)
    if not isinstance(fps, (int, float)) or not math.isfinite(fps) or not 1 <= fps <= 30:
        raise ValueError("A recorded frame rate of 1–30 is required.")
    loop = report.get("loop_mode")
    if loop not in {"once", "ping-pong"} or (loop == "ping-pong" and report.get("ping_pong_endpoints") != "single"):
        raise ValueError("Re-export older loops with single endpoints before comparison.")
    seconds = report.get("max_seconds", 0)
    if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0.5 <= seconds <= 15:
        raise ValueError("A recorded source duration of 0.5–15 seconds is required.")
    with Image.open(preview) as image:
        width, height = image.size
        count = image.n_frames
        if image.format != "WEBP" or not 2 <= count <= 900 or not 64 <= width <= 720 or height > 1024:
            raise ValueError("Review is limited to short, scaled WebP animations.")
        if loop == "ping-pong" and width * height * (count // 2 + 1) * 4 > 300_000_000:
            raise ValueError("Reduce the preview size before buffering the source comparison reverse pass.")
        durations = []
        for index in range(count):
            image.seek(index)
            image.load()
            durations.append(image.info.get("duration", 0))
        # Integer millisecond WebP timestamps can round a 24 FPS frame to 41/42.
        # Do not flatten an authored pause or manufacture an increased frame rate.
        if any(abs(duration - 1000 / fps) > 1.1 for duration in durations):
            raise ValueError("Variable timing contains authored pauses; constant-FPS review would change it.")
        if count != report.get("encoded_frames") or sum(durations) != report.get("duration_ms"):
            raise ValueError("Frame timing does not match the preparation report.")
        if abs(sum(durations) - count * 1000 / fps) > 2:
            raise ValueError("Frame timing would drift during constant-FPS conversion.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nijika-review-", dir=destination.parent) as temporary:
        scratch = Path(temporary)
        transparent = scratch / "transparent.webm"
        writer = imageio_ffmpeg.write_frames(
            str(transparent), (width, height), pix_fmt_in="rgba", pix_fmt_out="yuva420p",
            fps=fps, codec="libvpx-vp9", macro_block_size=1, ffmpeg_log_level="error",
            ffmpeg_timeout=60, output_params=CODEC_OPTIONS[2:])
        writer.send(None)
        try:
            with Image.open(preview) as image:
                for index in range(count):
                    image.seek(index)
                    writer.send(image.convert("RGBA").tobytes())
        finally:
            writer.close()
        original = scratch / "source.webm"
        base = (f"trim=duration={seconds},setpts=PTS-STARTPTS,fps={fps:.8f},"
                f"scale={width}:{height}:flags=lanczos,format=yuv420p")
        if loop == "ping-pong":
            graph = (f"[0:v]{base},split=2[f][b];"
                     "[f]trim=start_frame=1,setpts=PTS-STARTPTS[steps];"
                     "[b]reverse,trim=start_frame=1,setpts=PTS-STARTPTS[back];"
                     "[steps][back]concat=n=2:v=1:a=0[result]")
            filters = ["-filter_complex", graph, "-map", "[result]"]
        else:
            filters = ["-vf", base]
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin",
             "-i", str(source), *filters, "-r", str(fps), "-fps_mode", "cfr", *CODEC_OPTIONS, str(original)],
            capture_output=True, timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise ValueError("Could not encode the source comparison video.")
        checks = {name: decode_metrics(scratch / name) for name in ("transparent.webm", "source.webm")}
        if any(item["frames"] != count or item["size"] != [width, height] for item in checks.values()):
            raise ValueError("Comparison frame counts or dimensions differ; no output was published.")
        if any(abs(item["duration_seconds"] - count / fps) > 0.011 for item in checks.values()):
            raise ValueError("Comparison container durations differ; no output was published.")
        if not checks["transparent.webm"]["has_alpha"]:
            raise ValueError("The encoded comparison lost its alpha plane.")
        write_poster(scratch / "source.webm", scratch / "source-poster.png")
        write_poster(scratch / "transparent.webm", scratch / "transparent-poster.png")
        manifest = {"version": 1, "preview_only": True, "visual_acceptance": "pending",
                    "source_sha256": file_hash(source), "preview_sha256": file_hash(preview),
                    "source_name": source.name, "preview_name": preview.name,
                    "fps": fps, "frames": count, "size": [width, height], "loop_mode": loop,
                    "duration_seconds": count / fps, "timestamp_rounding_ms": count * 1000 / fps - sum(durations),
                    "python_frame_buffer_bytes": width * height * 4,
                    "buffer_note": "One RGBA frame is submitted at a time; encoder/decoder have their own buffers.",
                    "files": {name: {"sha256": file_hash(scratch / name), "bytes": (scratch / name).stat().st_size,
                                     **checks[name]} for name in checks},
                    "posters": {name: {"sha256": file_hash(scratch / name), "bytes": (scratch / name).stat().st_size}
                                for name in ("source-poster.png", "transparent-poster.png")}}
        (scratch / "review.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        # Never partially replace an existing review. The scratch directory is
        # removed on failure; once validated, publish the three files together.
        destination.mkdir()
        # Keep any partial directory explicit on a copy failure; a repeat
        # cannot overwrite it, and serve refuses incomplete/hash-mismatched data.
        for name in ("source.webm", "transparent.webm", "source-poster.png", "transparent-poster.png", "review.json"):
            shutil.copyfile(scratch / name, destination / name)
    return manifest


def byte_range(header: str | None, size: int) -> tuple[int, int, bool]:
    if header is None:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()):
        raise ValueError("Unsupported byte range")
    start_text, end_text = match.groups()
    if not start_text:
        length = int(end_text)
        if not length:
            raise ValueError("Empty suffix")
        start, end = max(0, size - length), size - 1
    else:
        start, end = int(start_text), min(int(end_text) if end_text else size - 1, size - 1)
    if not 0 <= start <= end < size:
        raise ValueError("Unsatisfiable range")
    return start, end, True


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, directory: Path, port: int = 0):
        directory = directory.resolve(strict=True)
        self.manifest = json.loads((directory / "review.json").read_text(encoding="utf-8"))
        if self.manifest.get("version") != 1 or self.manifest.get("preview_only") is not True:
            raise ValueError("Not an isolated review export")
        for name in ("source.webm", "transparent.webm"):
            if file_hash(directory / name) != self.manifest["files"][name]["sha256"]:
                raise ValueError("Review file hash mismatch")
        for name in ("source-poster.png", "transparent-poster.png"):
            if file_hash(directory / name) != self.manifest["posters"][name]["sha256"]:
                raise ValueError("Review poster hash mismatch")
        self.assets = {"/": (ASSETS / "index.html", "text/html; charset=utf-8"),
                       "/review.js": (ASSETS / "review.js", "text/javascript; charset=utf-8"),
                       "/review.css": (ASSETS / "review.css", "text/css; charset=utf-8"),
                       "/review.json": (directory / "review.json", "application/json; charset=utf-8"),
                       "/source.webm": (directory / "source.webm", "video/webm"),
                       "/transparent.webm": (directory / "transparent.webm", "video/webm"),
                       "/source-poster.png": (directory / "source-poster.png", "image/png"),
                       "/transparent-poster.png": (directory / "transparent-poster.png", "image/png")}
        super().__init__(("127.0.0.1", port), ReviewHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


class ReviewHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_HEAD(self):
        self.serve(head=True)

    def do_GET(self):
        self.serve(head=False)

    def serve(self, *, head: bool):
        if (self.headers.get("Host") != self.server.origin.removeprefix("http://")
                or self.headers.get("Origin", self.server.origin) != self.server.origin
                or self.headers.get("Sec-Fetch-Site", "none") not in {"none", "same-origin"}):
            self.send_error(403)
            return
        route = urlsplit(self.path).path
        asset = self.server.assets.get(route)
        if asset is None:
            self.send_error(404)
            return
        path, content_type = asset
        size = path.stat().st_size
        try:
            start, end, partial = byte_range(self.headers.get("Range"), size)
        except ValueError:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if not head:
            try:
                with path.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = stream.read(min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Seeking/cancelling a video normally closes its old range.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("source", type=Path)
    export.add_argument("preview", type=Path)
    export.add_argument("destination", type=Path)
    serve = commands.add_parser("serve")
    serve.add_argument("directory", type=Path)
    serve.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.command == "export":
        print(json.dumps(export_review(args.source, args.preview, args.destination), ensure_ascii=False, indent=2))
    else:
        with ReviewServer(args.directory, args.port) as server:
            print(server.origin, flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
