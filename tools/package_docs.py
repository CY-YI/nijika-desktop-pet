"""Build the current shareable documentation bundle from tracked source files."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "项目概览-对外分享.md",
    "README.md",
    "INSTALL.md",
    "REQUIREMENTS.md",
    "ARCHITECTURE.md",
    "INTERFACES.md",
    "CHANGELOG.md",
    "TODO.md",
    "AGENTS.md",
    "art/PROMPTS.md",
    "art/bubble-preview.png",
    "art/motion-preview.gif",
    "skills/nijika-desktop-dialog/SKILL.md",
    "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md",
    "integrations/dsh/README.md",
    "integrations/dsh/nijika-dsh-dialog/SKILL.md",
    "distribution/README.md",
    "AGENT_SETUP.md",
)
PREFIX = "虹夏桌宠-项目文档与预览"


def package(output: Path) -> None:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing documentation files: {', '.join(missing)}")
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(
            f"{PREFIX}/文档目录.md",
            "# 文档目录\n\n先看《项目概览-对外分享.md》，再看 README.md 和 INSTALL.md。"
            "本包包含项目文档、三份桌宠交互技能说明和效果预览；"
            "不包含 EXE、完整源码或角色素材复用许可。\n",
        )
        for name in FILES:
            archive.write(ROOT / name, f"{PREFIX}/{name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / f"{PREFIX}-{date.today().isoformat()}.zip",
    )
    destination = parser.parse_args().output
    package(destination)
    print(destination)
