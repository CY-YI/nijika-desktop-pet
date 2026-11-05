"""Continuous local deformation for the interaction settings preview.

The original illustration stays intact. A smooth inverse mesh bends the head,
ponytail and limbs independently, with every action returning to a neutral pose.
"""
from __future__ import annotations

import io
import math
from PIL import Image, ImageDraw

ACTIONS = {
    "pet": ("摸摸头", 2.0, "happy", "再摸一下嘛，今天也辛苦啦。"),
    "poke": ("戳戳脸", 1.6, "pout", "咦？被你发现我在发呆啦。"),
    "nod": ("点点头", 2.0, "happy", "嗯嗯，我在认真听呢。"),
    "shake": ("摇摇头", 2.2, "wink", "才没有偷偷打瞌睡呢！"),
    "dance": ("坐姿小舞", 3.2, "excited", "休息几秒，跟着节奏晃一晃吧！"),
    "lift": ("提起晃晃", 2.0, "worried", "轻一点，我会乖乖坐好的。"),
    "feed": ("吃点心", 2.2, "happy", "谢谢投喂！又有精神陪你啦。"),
    "drink": ("喝口水", 2.2, "happy", "咕噜咕噜……你也记得喝水呀。"),
}


def smooth(low: float, high: float, value: float) -> float:
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def hit_region(x: float, y: float) -> str:
    """Coordinates are relative to the complete character window, not screen."""
    if y < 0.30:
        return "pet"
    if y < 0.53 and 0.18 < x < 0.73:
        return "poke"
    return "nod"


def motion_at(action: str, elapsed: float) -> dict:
    if action not in ACTIONS:
        raise ValueError("不支持这个互动动作。")
    duration = ACTIONS[action][1]
    t = max(0.0, min(1.0, elapsed / duration))
    envelope = math.sin(math.pi * t) ** 2
    beat = math.sin(t * math.pi * (8 if action == "dance" else 4))
    delayed = math.sin(t * math.pi * 4 - 0.7)
    pose = dict(head=0.0, drop=0.0, tail=0.0, legs=0.0, hands=0.0,
                press=0.0, hearts=0.0, snack=0.0)
    if elapsed < 0 or elapsed >= duration:
        return pose
    if action == "pet":
        pose.update(head=2.2 * beat, drop=0.008 * (beat + 1), tail=0.018 * delayed,
                    hearts=envelope)
    elif action == "poke":
        pose.update(head=-3.5 * beat, press=0.014 * (1 - t), tail=0.012 * delayed)
    elif action == "nod":
        pose.update(drop=0.014 * (beat + 1), head=1.4 * beat, tail=0.013 * delayed)
    elif action == "shake":
        pose.update(head=5.5 * beat, tail=-0.024 * delayed, hands=0.003 * beat)
    elif action == "dance":
        pose.update(head=4.0 * beat, drop=0.007 * abs(beat), tail=-0.03 * delayed,
                    legs=0.025 * beat, hands=-0.013 * beat, hearts=0.6 * envelope)
    elif action == "lift":
        pose.update(head=4.0 * beat, tail=0.027 * delayed, legs=0.016 * delayed,
                    hands=0.012 * beat)
    else:
        pose.update(drop=0.008 * (beat + 1), tail=0.012 * delayed,
                    hearts=0.7 * envelope, snack=envelope)
    for key in ("head", "drop", "tail", "legs", "hands", "press"):
        pose[key] *= envelope
    return pose


def _inverse_point(x: float, y: float, p: dict) -> tuple[float, float]:
    head = 1.0 - smooth(0.45, 0.59, y)
    theta = math.radians(p["head"] * head)
    dx, dy = x - 0.45, y - 0.51
    # Correct the rotation for a canvas whose height is 1.5 times its width.
    sx = 0.45 + math.cos(theta) * dx + math.sin(theta) * dy * 1.5
    sy = 0.51 - math.sin(theta) * dx / 1.5 + math.cos(theta) * dy
    sy -= p["drop"] * head
    tail = smooth(0.69, 0.86, x) * smooth(0.17, 0.48, y) * (1 - smooth(0.61, 0.69, y))
    sx -= p["tail"] * tail
    legs = smooth(0.71, 0.95, y) * (1 - smooth(0.71, 0.85, x)) * smooth(0.16, 0.29, x)
    sx -= p["legs"] * legs * (1 if x < 0.48 else -1)
    sy += p["legs"] * 0.2 * legs
    hand = math.exp(-((y - 0.68) / 0.065) ** 2) * (1 - math.exp(-((x - 0.46) / 0.21) ** 2))
    sy -= p["hands"] * hand * (1 if x < 0.46 else -1)
    cheek = math.exp(-((x - 0.32) / 0.12) ** 2 - ((y - 0.40) / 0.09) ** 2)
    sx += p["press"] * cheek
    return sx, sy


def render_interaction(source: Image.Image, action: str, elapsed: float,
                       strength: float = 1.0, effects: bool = True) -> Image.Image:
    p = motion_at(action, elapsed)
    width, height = source.size
    strength = max(0.0, min(1.0, strength))
    if strength == 0 or not any(p.values()):
        return source.copy()
    p = {key: value * strength for key, value in p.items()}
    mesh = []
    columns, rows = 12, 22
    for row in range(rows):
        for col in range(columns):
            left, right = round(col * width / columns), round((col + 1) * width / columns)
            top, bottom = round(row * height / rows), round((row + 1) * height / rows)
            quad = []
            for x, y in ((left, top), (left, bottom), (right, bottom), (right, top)):
                sx, sy = _inverse_point(x / width, y / height, p)
                quad.extend((sx * width, sy * height))
            mesh.append(((left, top, right, bottom), quad))
    canvas = source.transform(source.size, Image.Transform.MESH, mesh,
                              Image.Resampling.BILINEAR, fillcolor=(0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    if effects and p["hearts"] > 0.01:
        for x, y, offset in ((0.19, 0.20, 0), (0.83, 0.13, 0.06), (0.85, 0.36, 0.03)):
            cx, cy = width * x, height * (y - 0.035 * elapsed + offset)
            size = width * 0.013
            points = []
            for i in range(41):
                a = i * math.tau / 40
                points.append((cx + size * 0.6 * 16 * math.sin(a) ** 3 / 10,
                               cy - size * 0.6 * (13 * math.cos(a) - 5 * math.cos(2*a)
                                                - 2 * math.cos(3*a) - math.cos(4*a)) / 10))
            draw.polygon(points, fill=(239, 123, 140, round(240 * p["hearts"])))
    if effects and p["snack"] > 0.05:
        cx, cy = width * 0.45, height * (0.54 - 0.055 * p["snack"])
        radius = width * 0.045
        color = (227, 173, 107, 250) if action == "feed" else (174, 218, 234, 250)
        draw.rounded_rectangle((cx-radius, cy-radius, cx+radius, cy+radius),
                               radius=round(radius if action == "feed" else radius/3),
                               fill=color, outline=(132, 99, 80, 255), width=2)
        if action == "feed":
            for dx, dy in ((-0.4, -0.3), (0.3, 0.3), (0.4, -0.4)):
                draw.ellipse((cx+dx*radius-1, cy+dy*radius-1,
                              cx+dx*radius+2, cy+dy*radius+2), fill=(114, 76, 63, 255))
    return canvas


def preview_webp(source: Image.Image, action: str, strength: float = 1.0,
                 effects: bool = True) -> bytes:
    """One bounded action at 60 samples/second, ending at the original pose."""
    if action not in ACTIONS:
        raise ValueError("不支持这个互动动作。")
    count = round(ACTIONS[action][1] * 60)
    frames = [render_interaction(source, action, i / 60, strength, effects) for i in range(count + 1)]
    output = io.BytesIO()
    durations = [round((i + 1) * 1000 / 60) - round(i * 1000 / 60) for i in range(count)]
    durations.append(500)
    frames[0].save(output, format="WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=1, quality=94, method=2)
    return output.getvalue()
