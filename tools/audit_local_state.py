"""Read-only audit of local Nijika settings, skins and saved Agent profiles."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from control_store import ControlStore, DEFAULTS, IDENTIFIER, SPRITES
from notification_store import default_database_path
from skin_animation import validate_animation


def audit(database: Path) -> dict:
    database = database.expanduser().resolve()
    if not database.is_file():
        return {
            "status": "missing",
            "database": str(database),
            "error": "local database does not exist",
        }

    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    state_error = None
    try:
        try:
            settings_row = connection.execute(
                "SELECT value FROM panel_preferences WHERE name='settings'"
            ).fetchone()
            settings = (
                {**DEFAULTS, "revision": 0, **json.loads(settings_row[0])}
                if settings_row
                else {**DEFAULTS, "revision": 0}
            )
            agent_rows = connection.execute(
                "SELECT value FROM panel_agents ORDER BY rowid"
            ).fetchall()
            agents = [json.loads(row[0]) for row in agent_rows]
        except (sqlite3.Error, json.JSONDecodeError, TypeError, AttributeError) as error:
            state_error = type(error).__name__
            settings = {**DEFAULTS, "revision": 0}
            agents = []
    finally:
        connection.close()

    skin_root = database.parent / "skins"
    skins = [
        {
            "id": "default",
            "name": "虹夏 · 经典制服",
            "kind": "expressions",
            "builtin": True,
        }
    ]
    invalid_skins = []
    for manifest_path in sorted(skin_root.glob("*/manifest.json")):
        skin_id = manifest_path.parent.name
        try:
            if not IDENTIFIER.fullmatch(skin_id):
                raise ValueError("skin directory ID is not a 32-character lowercase hex value")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("manifest must be a JSON object")
            for sprite in SPRITES:
                image_path = manifest_path.parent / f"{sprite}.png"
                if not image_path.is_file():
                    raise ValueError(f"missing expression image: {sprite}.png")
                ControlStore.read_image(image_path.read_bytes())
            animation = validate_animation(manifest.get("idle"))
            if animation:
                for filename in animation["frames"]:
                    frame = manifest_path.parent / filename
                    if not frame.is_file():
                        raise ValueError(f"missing idle frame: {filename}")
                    ControlStore.read_image(frame.read_bytes())
            skins.append(
                {
                    "id": skin_id,
                    "name": str(manifest.get("name", skin_id))[:40],
                    "kind": manifest.get("kind", "expressions"),
                    "builtin": False,
                    "idle_frame_count": (
                        len(animation["frames"]) if animation else 0
                    ),
                }
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            invalid_skins.append(
                {"id": skin_id, "path": str(manifest_path.parent), "error": str(error)}
            )

    selected = settings.get("skin", "default")
    selected_present = any(item["id"] == selected for item in skins)
    complete_keys = [
        (
            str(item.get("client", "")),
            str(item.get("location", "")),
            str(item.get("agent_identity", "")),
            str(item.get("software", "")),
        )
        for item in agents
        if item.get("agent_identity") and item.get("software")
    ]
    duplicate_complete_agent_keys = [
        {
            "client": key[0],
            "location": key[1],
            "agent_identity": key[2],
            "software": key[3],
            "count": count,
        }
        for key, count in Counter(complete_keys).items()
        if count > 1
    ]
    legacy_custom_profiles = [
        {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "location": item.get("location", ""),
        }
        for item in agents
        if item.get("client") == "custom"
        and (not item.get("agent_identity") or not item.get("software"))
    ]
    issues = []
    if state_error:
        issues.append({"kind": "invalid_local_state", "error_type": state_error})
    if not selected_present:
        issues.append({"kind": "missing_selected_skin", "skin": selected})
    issues.extend(
        {"kind": "invalid_skin", **item}
        for item in invalid_skins
    )
    issues.extend(
        {"kind": "duplicate_complete_agent", **item}
        for item in duplicate_complete_agent_keys
    )
    return {
        "status": "conflict" if issues else "clean",
        "database": str(database),
        "settings_valid": state_error is None,
        "local_state_error": state_error,
        "settings_revision": settings.get("revision", 0),
        "selected_skin": selected,
        "selected_skin_present": selected_present,
        "skin_count_including_default": len(skins),
        "skins": skins,
        "invalid_skins": invalid_skins,
        "agent_count": len(agents),
        "legacy_custom_profiles": legacy_custom_profiles,
        "duplicate_complete_agent_keys": duplicate_complete_agent_keys,
        "issues": issues,
        "scope": (
            "Read-only local state audit; legacy custom profiles are preserved "
            "because missing identity must not be guessed."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path,
                        default=default_database_path())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.database)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if report["status"] != "clean":
        raise SystemExit(1)
