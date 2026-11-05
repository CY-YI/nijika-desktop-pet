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
        actions=("知道了",), kind="agent", duration=None, request_id="preview-completion",
    )
)[0]
choice = render_bubble(
    BubbleNotice(
        "Codex · 文案审阅", "双击“虹夏桌宠.exe”即可看到坐姿角色。Codex 完成任务后，桌宠可显示提醒与选择。接受这段说明吗？",
        actions=("接受文案", "需要修改"),
        action_descriptions=(
            "文案已经完整，可直接采用并继续下一步。",
            "暂不定稿，后续再说明修改要求。",
        ),
        action_recommended=(True, False),
        kind="agent", duration=None, request_id="preview",
    )
)[0]
preview = Image.new("RGBA", (1350, max(450, choice.height + 20)), (242, 238, 232, 255))
preview.alpha_composite(daily, (10, 10))
preview.alpha_composite(agent, (460, 10))
preview.alpha_composite(choice, (910, 10))
output = ROOT / "art" / "bubble-preview.png"
preview.convert("RGB").save(output)
print(output)
