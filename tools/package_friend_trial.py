"""Build a small private Windows friend-trial ZIP around the reviewed Setup EXE."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETUP = ROOT / "dist-release" / "installer-0.1.9" / "虹夏桌宠-Setup-0.1.9.exe"
DEFAULT_MANIFEST = ROOT / "dist-release" / "installer-0.1.9" / "installer-manifest.json"
DEFAULT_AGENT_SETUP = ROOT / "AGENT_SETUP.md"
DEFAULT_FRIEND_GUIDE = ROOT / "FRIEND_TRIAL_GUIDE.md"
DEFAULT_OUTPUT = ROOT / "dist-release" / "friend-trial-0.1.9-release" / "虹夏桌宠-v0.1.9-朋友试用包.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def guide(setup_digest: str, version: str, filename: str) -> str:
    return f"""虹夏桌宠 v{version}｜朋友私下试用

适用：Windows 10/11 x64。

1. 解压整个压缩包。
2. 双击“{filename}”，按向导选择安装目录、桌面快捷方式和开机自启。
3. 安装后打开“虹夏桌宠设置”→“Agent 接入”→“扫描本机”，选择要接入的客户端，再预览并应用。
4. 按页面提示重启客户端或新建任务。Codex 如果提示信任 /hooks，请由本人审阅并信任。
5. 查看接入步骤的通知能力清单：Codex/DSH 可接结束事件，需分别验收；Work 等其他客户端目前仅主动调用，仍可能漏提醒。无需每轮重新配置。
6. DSH 模块接口核对版本为 0.2.1-rc.2 / 0.2.1-rc.3；重启后用新会话测试。MAGPIE 管理项须由配置所有者审阅合并事件模块。
7. 单独测试不提虹夏的短问答、主动通知后不重复、后台/并行任务隔离。面板测试不能代替真实客户端验收。

说明：安装器默认不会覆盖外部 Agent 配置；首次使用需要在设置中心完成接入。
Work 仅支持本机任务，普通云端聊天不能直接访问本机程序。

这是非官方同人项目的私下测试包，请勿公开上架或转发到公开下载站。
角色素材与图标的公开再分发权仍需另行确认。

安装器 SHA-256：
{setup_digest}
"""


def build(output: Path, setup: Path, manifest: Path, agent_setup: Path,
          friend_guide: Path = DEFAULT_FRIEND_GUIDE) -> dict[str, object]:
    if not setup.is_file():
        raise FileNotFoundError(f"Missing Setup EXE: {setup}")
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing installer manifest: {manifest}")
    if not agent_setup.is_file():
        raise FileNotFoundError(f"Missing Agent setup guide: {agent_setup}")
    if not friend_guide.is_file():
        raise FileNotFoundError(f"Missing friend guide: {friend_guide}")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    version = str(manifest_data.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", version):
        raise ValueError("Invalid installer manifest version")
    archive_root = f"虹夏桌宠-v{version}-朋友私下试用"
    actual_digest = sha256(setup)
    expected_digest = str(manifest_data.get("sha256", "")).lower()
    if expected_digest != actual_digest:
        raise ValueError(f"Setup hash mismatch: manifest={expected_digest}, actual={actual_digest}")
    output.parent.mkdir(parents=True, exist_ok=True)
    guide_bytes = guide(actual_digest, version, setup.name).encode("utf-8")
    output.unlink(missing_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(setup, f"{archive_root}/{setup.name}")
        archive.write(manifest, f"{archive_root}/{manifest.name}")
        archive.write(agent_setup, f"{archive_root}/{agent_setup.name}")
        archive.write(friend_guide, f"{archive_root}/{friend_guide.name}")
        archive.writestr(f"{archive_root}/朋友试用说明.txt", guide_bytes)
    return {
        "status": "built",
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "setup_sha256": actual_digest,
        "files": [setup.name, manifest.name, agent_setup.name, friend_guide.name, "朋友试用说明.txt"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent-setup", type=Path, default=DEFAULT_AGENT_SETUP)
    parser.add_argument("--friend-guide", type=Path, default=DEFAULT_FRIEND_GUIDE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.setup, args.manifest, args.agent_setup,
                           args.friend_guide),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
