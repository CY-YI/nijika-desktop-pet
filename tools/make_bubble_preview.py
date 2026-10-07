"""Recreate the daily, completion, and explained-choice bubble examples."""

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
choice = render_bubble(
    BubbleNotice(
        "Codex · 下一步", "接下来怎样展示任务提醒？",
        actions=("简洁气泡", "详细卡片"),
        action_descriptions=(
            "只显示关键结论，减少打断。",
            "补充背景和可选步骤，便于判断。",
        ),
        kind="agent", duration=None, request_id="preview",
    )
)[0]
preview = Image.new("RGBA", (1350, 450), (242, 238, 232, 255))
preview.alpha_composite(daily, (10, 10))
preview.alpha_composite(agent, (460, 10))
preview.alpha_composite(choice, (910, 10))
output = ROOT / "art" / "bubble-preview.png"
preview.convert("RGB").save(output)
print(output)
