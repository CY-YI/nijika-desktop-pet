"""Convert a short, solid-blue reference video into an isolated WebP preview.

This performs technical conversion, not art generation or automatic visual
acceptance. It never installs the result as a pet skin or replaces input files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence


def video_metadata(source: Path) -> dict:
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(str(source))
    try:
        return next(reader)
    finally:
        reader.close()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def webp_metrics(path: Path) -> dict:
    durations, unique, transparent = [], set(), False
    with Image.open(path) as image:
        for frame in ImageSequence.Iterator(image):
            rgba = frame.convert("RGBA")
            durations.append(frame.info.get("duration", 0))
            unique.add(hashlib.sha256(rgba.tobytes()).digest())
            transparent |= rgba.getchannel("A").getextrema()[0] == 0
        return {"size": list(image.size), "encoded_frames": len(durations),
                "duration_ms": sum(durations), "unique_frames": len(unique),
                "has_transparent_pixels": transparent}


def prepare(source: Path, destination: Path, *, width: int = 360,
            fps_cap: float = 24, max_seconds: float = 12,
            similarity: float = 0.12, blend: float = 0.06,
            key_color: str = "#0000FF", lossless: bool = True,
            quality: int = 85, clean_blue_shadows: bool = False,
            loop_mode: str = "once", shadow_region: tuple[float, float, float, float] | None = None) -> dict:
    if not 64 <= width <= 720 or not 1 <= fps_cap <= 30 or not 0.5 <= max_seconds <= 15:
        raise ValueError("Use width 64–720, fps cap 1–30, and duration 0.5–15 seconds.")
    if not 0.01 <= similarity <= 0.3 or not 0 <= blend <= 0.3:
        raise ValueError("Blue key similarity must be 0.01–0.3 and blend 0–0.3.")
    if not isinstance(lossless, bool) or not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError("Use a boolean lossless mode and quality 1–100.")
    if not isinstance(clean_blue_shadows, bool) or loop_mode not in {"once", "ping-pong"}:
        raise ValueError("Use a boolean shadow cleanup and loop mode once or ping-pong.")
    if clean_blue_shadows:
        if shadow_region is None or len(shadow_region) != 4:
            raise ValueError("Specify a normalized shadow region; do not key overlays across the whole frame.")
        if not all(math.isfinite(value) for value in shadow_region):
            raise ValueError("Shadow coordinates must be finite.")
        x0, y0, x1, y1 = shadow_region
        if not 0 <= x0 < x1 <= 1 or not 0 <= y0 < y1 <= 1:
            raise ValueError("Use shadow coordinates x0 y0 x1 y1 within 0–1.")
    elif shadow_region is not None:
        raise ValueError("A shadow region requires explicit blue shadow cleanup.")
    try:
        if len(key_color) != 7 or not key_color.startswith("#"):
            raise ValueError
        red, green, blue = (int(key_color[i:i + 2], 16) for i in (1, 3, 5))
    except (TypeError, ValueError):
        raise ValueError("Use a blue key color in #RRGGBB form.") from None
    if blue <= red or blue < green + 10:
        raise ValueError("Use a blue background; green keys would damage the character's jacket.")
    key_color = f"#{red:02X}{green:02X}{blue:02X}"
    source, destination = source.resolve(strict=True), destination.resolve()
    sidecar = destination.with_suffix(destination.suffix + ".json")
    if destination.suffix.lower() != ".webp":
        raise ValueError("The output must be a new .webp preview file.")
    if destination.exists() or sidecar.exists():
        raise FileExistsError("Preview or report already exists; choose a new output name.")
    meta = video_metadata(source)
    source_width, source_height = meta["size"]
    source_fps = float(meta["fps"])
    if not math.isfinite(source_fps) or not 0 < source_fps <= 240:
        raise ValueError("A valid source frame rate is required; do not guess or upsample.")
    if not 1 <= source_width * source_height <= 8_000_000:
        raise ValueError("Source dimensions exceed the eight-megapixel preview limit.")
    target_width = min(width, source_width)
    target_height = max(1, round(source_height * target_width / source_width))
    if target_height > 2048:
        raise ValueError("The source aspect ratio is unsuitable for this preview.")
    target_fps = min(source_fps, fps_cap)
    # Reverse buffers a complete scaled clip; bound its working-set estimate.
    if loop_mode == "ping-pong" and target_width * target_height * target_fps * max_seconds * 4 > 300_000_000:
        raise ValueError("Reduce width, FPS or duration before buffering a ping-pong preview.")
    import imageio_ffmpeg
    filter_chain = (f"trim=duration={max_seconds},setpts=PTS-STARTPTS,fps={target_fps:.8f},"
                    f"format=rgba,colorkey=0x{key_color[1:]}:{similarity}:{blend}")
    if clean_blue_shadows:
        # Restrict to a visually checked region: translucent white overlays on
        # blue can also be blue-dominant, so a global color rule would erase them.
        x0, y0, x1, y1 = shadow_region
        inside = f"between(X/W,{x0},{x1})*between(Y/H,{y0},{y1})"
        filter_chain += (",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                         f"a='if({inside},alpha(X,Y)*clip((25-b(X,Y)+max(r(X,Y),g(X,Y)))/8,0,1),alpha(X,Y))'")
    filter_chain += (f",format=rgba,despill=type=blue:mix=0.3:blue=-1,"
                     f"scale={target_width}:{target_height}:flags=lanczos")
    if loop_mode == "ping-pong":
        # Traverse each endpoint once. Starting the forward half at frame 1
        # lets the reverse half end at frame 0, adjacent to the next loop's 1.
        # Keeping both endpoints twice creates a visible two-frame hold.
        graph = (f"[0:v]{filter_chain},split=2[forward][backward];"
                 "[forward]trim=start_frame=1,setpts=PTS-STARTPTS[forward_steps];"
                 "[backward]reverse,trim=start_frame=1,setpts=PTS-STARTPTS[reversed];"
                 "[forward_steps][reversed]concat=n=2:v=1:a=0[animation]")
        filter_arguments = ["-filter_complex", graph, "-map", "[animation]"]
    else:
        filter_arguments = ["-vf", filter_chain]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nijika-clip-", dir=destination.parent) as temporary:
        candidate = Path(temporary) / "preview.webp"
        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin",
                   "-i", str(source), "-an", "-sn", *filter_arguments,
                   "-c:v", "libwebp_anim", "-lossless", str(int(lossless)), "-quality", str(quality),
                   "-compression_level", "4", "-loop", "0", str(candidate)]
        result = subprocess.run(command, capture_output=True, timeout=180, check=False,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode or not candidate.is_file():
            raise ValueError("Video conversion failed; inspect the source format and local FFmpeg installation.")
        metrics = webp_metrics(candidate)
        if metrics["duration_ms"] <= 0 or metrics["unique_frames"] < 2:
            raise ValueError("No actual animation was decoded; a still image is not an animation sample.")
        if not metrics["has_transparent_pixels"]:
            raise ValueError("No blue background was removed; inspect the source before changing key settings.")
        report = {"preview_only": True, "input_sha256": file_hash(source),
                  "output_sha256": file_hash(candidate), "source_fps": source_fps,
                  "sample_fps": target_fps, "key_color": key_color, "similarity": similarity,
                  "lossless": lossless, "quality": quality,
                  "clean_blue_shadows": clean_blue_shadows, "loop_mode": loop_mode,
                  "ping_pong_endpoints": "single" if loop_mode == "ping-pong" else None,
                  "shadow_region": shadow_region,
                  "blend": blend, "source_duration_seconds": meta.get("duration", 0),
                  "max_seconds": max_seconds, "visual_acceptance": "pending", **metrics}
        written = []
        try:
            with destination.open("xb") as output:
                written.append(destination)
                with candidate.open("rb") as stream:
                    shutil.copyfileobj(stream, output)
            with sidecar.open("x", encoding="utf-8") as output:
                written.append(sidecar)
                json.dump(report, output, ensure_ascii=False, indent=2)
        except OSError:
            for path in written:
                path.unlink(missing_ok=True)
            raise
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--fps-cap", type=float, default=24)
    parser.add_argument("--max-seconds", type=float, default=12)
    parser.add_argument("--similarity", type=float, default=0.12)
    parser.add_argument("--blend", type=float, default=0.06)
    parser.add_argument("--key-color", default="#0000FF", help="Observed blue background in #RRGGBB form")
    parser.add_argument("--lossy", dest="lossless", action="store_false", help="Smaller review copy; keep the source")
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--clean-blue-shadows", action="store_true", help="Only for characters without blue details")
    parser.add_argument("--loop-mode", choices=("once", "ping-pong"), default="once")
    parser.add_argument("--shadow-region", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"))
    args = parser.parse_args()
    print(json.dumps(prepare(**vars(args)), ensure_ascii=False))
