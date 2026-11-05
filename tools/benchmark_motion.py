"""Measure the full per-frame Pillow-to-DIB rendering path at each pet size."""

import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pet import SpriteSet  # noqa: E402


for width in (260, 320, 380):
    sprites = SpriteSet(width, width * 3 // 2)
    samples = []
    try:
        for frame in range(150):
            phase = frame / 60 * 2 * math.pi
            start = time.perf_counter()
            sprites.render(
                "happy", shift_y=-10 * math.sin(phase),
                angle=1.25 * math.sin(phase / 2),
                scale_x=1.0 + 0.004 * math.sin(phase),
                scale_y=1.0 + 0.006 * math.sin(phase),
                sparkle=max(0.0, math.sin(phase)),
            )
            samples.append((time.perf_counter() - start) * 1000)
    finally:
        sprites.close()
    samples = samples[10:]  # exclude first-use setup
    p95 = sorted(samples)[int(len(samples) * 0.95)]
    print(f"{width}px: median={statistics.median(samples):.2f}ms p95={p95:.2f}ms")
