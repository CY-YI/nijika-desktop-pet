"""Recreate the two visual examples of the desktop speech bubble."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pet import BubbleNotice, render_bubble  # noqa: E402

daily = render_bubble(BubbleNotice("虹夏 · 日常", "今天也要记得喝水呀。"))[0]
agent = render_bubble(
    BubbleNotice(
        "演示提醒 · Codex", "任务已完成，等待你查看结果。",
        actions=("已查看", "稍后"), kind="agent", duration=None,
    )
)[0]
preview = Image.new("RGBA", (900, 320), (242, 238, 232, 255))
preview.alpha_composite(daily, (10, 10))
preview.alpha_composite(agent, (460, 10))
output = ROOT / "art" / "bubble-preview.png"
preview.convert("RGB").save(output)
print(output)