"""Read-only audit of shipped and installed Nijika skills; never emit configs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
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
    conflicts = []
    duplicates = []
    for name, source, installed in definitions:
        text = source.read_text(encoding="utf-8-sig")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        copies = []
        for path in installed:
            exists = path.is_file()
            matches = exists and hashlib.sha256(path.read_bytes()).hexdigest() == digest
            state = "missing" if not exists else "matches" if matches else "conflict"
            copies.append({"path": str(path), "exists": exists, "matches_source": matches,
                           "state": state})
            if exists and not matches:
                conflicts.append({"kind": "content_mismatch", "client": name, "path": str(path)})
        matching_paths = [item["path"] for item in copies if item["matches_source"]]
        if len(matching_paths) > 1:
            duplicates.append({"kind": "duplicate_skill", "client": name, "paths": matching_paths})
        results.append({"client": name, "source": str(source), "source_sha256": digest,
                        "has_four_tool_names": all(tool in text for tool in
                            ("show_completion", "request_decision", "wait_for_reply", "get_reply")),
                        "describes_pending": "pending" in text,
                        "describes_late_reply": "ended" in text or "已结束" in text,
                        "installed": copies,
                        "status": "conflict" if any(item["state"] == "conflict" for item in copies)
                        else "duplicate" if len(matching_paths) > 1 else "clean"})
    issues = conflicts + duplicates
    return {"status": "conflict" if issues else "clean", "issues": issues, "skills": results,
            "work_launcher_dependencies": {
                "codex_cli_found": bool(shutil.which("codex")), "python_found": bool(shutil.which("python.exe"))},
            "scope": "Read-only file/skill audit. Does not prove a live client connected, reloaded or trusted hooks."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.home)
    result = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
    if report["status"] != "clean":
        raise SystemExit(1)
