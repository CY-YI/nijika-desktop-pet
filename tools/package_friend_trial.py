"""Build a small private Windows friend-trial ZIP around the reviewed Setup EXE."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETUP = ROOT / "dist-release" / "installer-0.1.7" / "虹夏桌宠-Setup-0.1.7.exe"
DEFAULT_MANIFEST = ROOT / "dist-release" / "installer-0.1.7" / "installer-manifest.json"
DEFAULT_OUTPUT = ROOT / "dist-release" / "friend-trial-0.1.7" / "虹夏桌宠-v0.1.7-朋友私下试用.zip"
ARCHIVE_ROOT = "虹夏桌宠-v0.1.7-朋友私下试用"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def guide(setup_digest: str) -> str:
    return f"""虹夏桌宠 v0.1.7｜朋友私下试用

适用：Windows 10/11 x64。

1. 解压整个压缩包。
2. 双击“虹夏桌宠-Setup-0.1.7.exe”，按向导选择安装目录、桌面快捷方式和开机自启。
3. 安装后打开“虹夏桌宠设置”→“Agent 接入”→“扫描本机”，选择要接入的客户端，再预览并应用。
4. 按页面提示重启客户端或新建任务。Codex 如果提示信任 /hooks，请由本人审阅并信任。
5. 接入完成后，不需要每轮对话前手动提醒 Agent；每个有效回复轮次都会尝试显示虹夏提醒。

说明：安装器默认不会覆盖外部 Agent 配置；首次使用需要在设置中心完成接入。
Work 仅支持本机任务，普通云端聊天不能直接访问本机程序。

这是非官方同人项目的私下测试包，请勿公开上架或转发到公开下载站。
角色素材与图标的公开再分发权仍需另行确认。

安装器 SHA-256：
{setup_digest}
"""


def build(output: Path, setup: Path, manifest: Path) -> dict[str, object]:
    if not setup.is_file():
        raise FileNotFoundError(f"Missing Setup EXE: {setup}")
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing installer manifest: {manifest}")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    actual_digest = sha256(setup)
    expected_digest = str(manifest_data.get("sha256", "")).lower()
    if expected_digest != actual_digest:
        raise ValueError(f"Setup hash mismatch: manifest={expected_digest}, actual={actual_digest}")
    output.parent.mkdir(parents=True, exist_ok=True)
    guide_bytes = guide(actual_digest).encode("utf-8")
    output.unlink(missing_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(setup, f"{ARCHIVE_ROOT}/{setup.name}")
        archive.write(manifest, f"{ARCHIVE_ROOT}/{manifest.name}")
        archive.writestr(f"{ARCHIVE_ROOT}/朋友试用说明.txt", guide_bytes)
    return {
        "status": "built",
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "setup_sha256": actual_digest,
        "files": [setup.name, manifest.name, "朋友试用说明.txt"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.setup, args.manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
