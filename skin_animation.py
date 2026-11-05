"""Bounded, data-only PNG timelines shared by import, preview and desktop."""
from __future__ import annotations

import bisect
import json
from pathlib import Path

MAX_FRAMES = 48
MAX_PIXELS = 24_000_000


def validate_animation(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"frames", "durations_ms"}:
        raise ValueError("idle 需要 frames 与 durations_ms 两项。")
    frames, durations = value["frames"], value["durations_ms"]
    if (not isinstance(frames, list) or not 2 <= len(frames) <= MAX_FRAMES
            or frames != [f"idle_{index:03d}.png" for index in range(len(frames))]):
        raise ValueError("待机需要 2–48 张连续命名的 idle_000.png 起始帧。")
    if (not isinstance(durations, list) or len(durations) != len(frames)
            or any(type(item) is not int or not 40 <= item <= 5000 for item in durations)
            or sum(durations) > 60_000):
        raise ValueError("每帧时长为 40–5000 毫秒，数量需与帧数一致，总长最多 60 秒。")
    return {"frames": list(frames), "durations_ms": list(durations)}


class SkinTimeline:
    def __init__(self, animation: dict | None):
        self.animation = validate_animation(animation)
        self.ends = []
        total = 0
        for duration in (self.animation or {}).get("durations_ms", []):
            total += duration
            self.ends.append(total)
        self.total = total

    @classmethod
    def load(cls, directory: Path) -> SkinTimeline:
        manifest = directory / "manifest.json"
        return cls(json.loads(manifest.read_text(encoding="utf-8")).get("idle")) if manifest.is_file() else cls(None)

    def frame(self, elapsed: float) -> str | None:
        if not self.total:
            return None
        index = bisect.bisect_right(self.ends, max(0, elapsed) * 1000 % self.total)
        return self.animation["frames"][index][:-4]
