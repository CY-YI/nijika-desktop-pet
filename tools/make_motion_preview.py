"""Render a GIF preview of continuous motion using the desktop rendering path."""

import math
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pet import SpriteSet, render_pose  # noqa: E402

OUT = ROOT / "art" / "motion-preview.gif"
sprites = SpriteSet(320, 480)
frames = []
try:
    for index in range(96):
        seconds = index / 32
        name = "curious" if seconds < 1 else "happy"
        breath = math.sin(seconds * 2 * math.pi / 1.55)
        angle = 1.25 * math.sin(seconds * 2 * math.pi / 2.65)
        shift_y = -1.5 * (breath + 1) / 2
        scale_x = 1 + 0.004 * breath
        scale_y = 1 + 0.006 * breath
        sparkle = 0.0
        if 1 <= seconds < 1.62:
            phase = (seconds - 1) / 0.62
            envelope = math.sin(math.pi * phase)
            lift = envelope ** 1.35
            shift_y -= 19 * lift
            scale_x += 0.025 * math.sin(2 * math.pi * phase) ** 2
            scale_y += 0.020 * lift - 0.022 * math.sin(2 * math.pi * phase) ** 2
            angle += 1.3 * math.sin(2 * math.pi * phase)
            sparkle = max(0.0, min(1.0, (lift - 0.35) * 2))
        sprite = render_pose(
            sprites.sources[name], shift_y=shift_y, angle=angle,
            scale_x=scale_x, scale_y=scale_y, sparkle=sparkle,
        )
        background = Image.new("RGB", sprite.size, (248, 248, 245))
        background.paste(sprite, mask=sprite.getchannel("A"))
        frames.append(background)
finally:
    sprites.close()

palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
indexed = [frame.quantize(palette=palette) for frame in frames]
OUT.parent.mkdir(parents=True, exist_ok=True)
indexed[0].save(
    OUT, save_all=True, append_images=indexed[1:],
    duration=31, loop=0, optimize=False,
)
print(OUT)
