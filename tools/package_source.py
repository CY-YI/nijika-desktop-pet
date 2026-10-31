"""Export an exact committed source snapshot plus optional reviewed executables."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
APPLICATIONS = ("虹夏桌宠.exe", "虹夏MCP-v2.exe", "虹夏审批提醒.exe")
BLOCKED = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "backups", "diagnostics",
    "build", "dist", "dist-dev", "dist-next", "dist-release", ".pyinstaller-cache",
}
PRIVATE_SUFFIXES = {".pyc", ".pyo", ".log", ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".pfx", ".p12"}
SECRETS = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    rb"|\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"
    rb"|\bsk-[A-Za-z0-9_-]{32,}"
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def build(output: Path, applications: Path | None = None) -> dict:
    if git("status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("Commit or otherwise preserve pending source changes before exporting.")
    revision = git("rev-parse", "HEAD").decode().strip()
    branch = git("branch", "--show-current").decode().strip()
    prefix = "虹夏桌宠-完整工程"
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", "HEAD"))) as archive:
        for member in archive:
            if member.isdir():
                continue
            path = PurePosixPath(member.name)
            if (not member.isfile() or path.is_absolute() or ".." in path.parts
                    or BLOCKED.intersection(path.parts) or path.suffix.lower() in PRIVATE_SUFFIXES
                    or path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example"):
                raise ValueError(f"Unexpected private/generated source entry: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Cannot read source entry: {member.name}")
            data = stream.read()
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp"}:
                if SECRETS.search(data):
                    raise ValueError(f"Potential credential in source entry: {member.name}")
            files[path.as_posix()] = data
    source_count = len(files)
    tracked_count = len([p for p in git("ls-tree", "-rz", "--name-only", "HEAD").split(b"\0") if p])
    if source_count != tracked_count:
        raise ValueError("The archive does not contain the complete committed source tree.")
    runtime_hashes = {}
    if applications:
        for name in APPLICATIONS:
            data = (applications / name).read_bytes()
            relative = f"dist/{name}"
            files[relative] = data
            runtime_hashes[relative] = hashlib.sha256(data).hexdigest()
    manifest = {
        "format_version": 1, "source_commit": revision, "source_branch": branch,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_files": source_count, "prebuilt_programs": runtime_hashes,
        "prebuilt_note": "Prebuilt programs are supplied for preview. Rebuild after changing source.",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
        "excluded": sorted(BLOCKED),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(f"{prefix}/{name}", data)
        archive.writestr(f"{prefix}/SOURCE_MANIFEST.json",
                         (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("The generated ZIP failed its integrity check.")
    return {
        "output": str(output), "source_commit": revision, "source_files": source_count,
        "prebuilt_programs": len(runtime_hashes), "total_entries": len(files) + 1,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--applications", type=Path,
                        help="Explicit reviewed directory containing all three runtime EXEs")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.applications), ensure_ascii=False, indent=2))
