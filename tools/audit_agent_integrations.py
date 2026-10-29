"""Read-only audit of shipped and installed Nijika skills; never emit configs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(home: Path) -> dict:
    codex = Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    definitions = (
        ("Codex", ROOT / "skills/nijika-desktop-dialog/SKILL.md",
         [codex / "skills/nijika-desktop-dialog/SKILL.md", home / ".agents/skills/nijika-desktop-dialog/SKILL.md"]),
        ("DSH", ROOT / "integrations/dsh/nijika-dsh-dialog/SKILL.md",
         [home / ".dsh/skills/nijika-dsh-dialog/SKILL.md", codex / "skills/nijika-dsh-dialog/SKILL.md"]),
        ("Work", ROOT / "plugins/nijika-work-local/skills/nijika-work-dialog/SKILL.md",
         sorted((codex / "plugins/cache/nijika-local").glob("nijika-work-local/*/skills/nijika-work-dialog/SKILL.md"))),
    )
    results = []
    for name, source, installed in definitions:
        text = source.read_text(encoding="utf-8-sig")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        results.append({"client": name, "source": str(source), "source_sha256": digest,
                        "has_four_tool_names": all(tool in text for tool in
                            ("show_completion", "request_decision", "wait_for_reply", "get_reply")),
                        "describes_pending": "pending" in text,
                        "describes_late_reply": "ended" in text or "已结束" in text,
                        "installed": [{"path": str(path), "exists": path.is_file(),
                                       "matches_source": path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest}
                                      for path in installed]})
    return {"skills": results, "work_launcher_dependencies": {
                "codex_cli_found": bool(shutil.which("codex")), "python_found": bool(shutil.which("python.exe"))},
            "scope": "Read-only file/skill audit. Does not prove a live client connected, reloaded or trusted hooks."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(args.home), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
